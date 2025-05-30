"""
Service for processing fetched price data and saving it to the database.
Also includes a service for managing and logging market update operations.
"""
import logging
from decimal import Decimal
from typing import Dict, Any, List, Tuple, Optional # Ensure Optional is imported
from django.utils import timezone
from django.db import transaction, IntegrityError

from apps.core.utils import PriceConverter, DateTimeHelper
from apps.market.models import PriceData, Commodity, MarketUpdate # Import MarketUpdate
from apps.core.exceptions import DataProcessingError, APIKeyMissingError, RateLimitExceededError, DataFetchError, ConfigurationError
from .data_fetcher import CommodityDataFetcherOrchestrator # Import the orchestrator

logger = logging.getLogger(__name__) # Define logger at module level


class PriceDataProcessor:
    """
    Service responsible for transforming raw data from different sources
    into PriceData model instances and saving them.
    """
    def __init__(self):
        self.price_converter = PriceConverter()
        self.date_helper = DateTimeHelper()
        self.logger = logging.getLogger(f"apps.{self.__class__.__module__}.{self.__class__.__name__}")


    def _prepare_price_data_entries(
        self,
        commodity: Commodity,
        parsed_items: List[Dict[str, Any]] # Each dict should have 'timestamp' and other price fields
    ) -> List[PriceData]:
        """
        Prepares a list of PriceData model instances from parsed items, avoiding duplicates.
        `parsed_items` is a list of dictionaries, each representing a potential PriceData record.
        Each dictionary must contain a 'timestamp' (datetime object) and price fields.
        """
        price_data_to_create = []
        
        # Get timestamps of items to potentially create
        timestamps_to_check = [item['timestamp'] for item in parsed_items if 'timestamp' in item and item['timestamp'] is not None]
        if not timestamps_to_check:
            return []

        # Find existing PriceData records for these timestamps and this commodity
        existing_timestamps = set(
            PriceData.objects.filter(
                commodity=commodity,
                timestamp__in=timestamps_to_check
            ).values_list('timestamp', flat=True)
        )
        self.logger.debug(f"For {commodity.symbol}, found {len(existing_timestamps)} existing timestamps out of {len(timestamps_to_check)} to check.")

        for item_data in parsed_items:
            timestamp = item_data.get('timestamp')
            if not timestamp or not isinstance(timestamp, timezone.datetime): # Ensure it's a datetime object
                self.logger.warning(f"Skipping entry for {commodity.symbol} due to invalid or missing timestamp: {timestamp}")
                continue

            if timestamp not in existing_timestamps:
                # Ensure close_price is valid before creating object
                if item_data.get('close_price') is None:
                    self.logger.warning(f"Skipping entry for {commodity.symbol} at {timestamp} due to missing 'close_price'. Data: {item_data}")
                    continue
                
                # Pop timestamp as it's a direct field, not in **defaults
                item_data.pop('timestamp', None) 
                
                price_data_to_create.append(
                    PriceData(
                        commodity=commodity,
                        timestamp=timestamp,
                        **item_data # Pass remaining fields as kwargs
                    )
                )
            # else:
            #     self.logger.debug(f"Price data for {commodity.symbol} at {timestamp} already exists. Skipping.")
        return price_data_to_create

    @transaction.atomic
    def _bulk_create_price_data(self, commodity: Commodity, price_data_list: List[PriceData]) -> int:
        """
        Bulk creates PriceData objects using a transaction.
        Returns the number of records successfully created.
        """
        if not price_data_list:
            return 0
        try:
            # ignore_conflicts=True means if a unique constraint (commodity, timestamp) is violated,
            # the conflicting row is ignored, and the process continues.
            # This is useful if the pre-check for existing timestamps isn't perfectly in sync
            # due to concurrent operations, though less likely in typical Celery task scenarios.
            created_objects = PriceData.objects.bulk_create(price_data_list, ignore_conflicts=True)
            num_created = len(created_objects) # bulk_create with ignore_conflicts on PostgreSQL returns objects that were created
            self.logger.info(f"Bulk created {num_created} new price data records for {commodity.symbol}.")
            return num_created
        except IntegrityError as e: # Should be rare with ignore_conflicts=True and pre-check
            self.logger.error(f"Integrity error during bulk create for {commodity.symbol}: {e}", exc_info=True)
            # Fallback or re-raise. For now, log and return 0 for this batch.
            return 0
        except Exception as e:
            self.logger.error(f"Unexpected error during bulk create for {commodity.symbol}: {e}", exc_info=True)
            raise DataProcessingError(f"Bulk creation of price data failed for {commodity.symbol}") from e

    def process_alpha_vantage_data(self, commodity: Commodity, raw_data: Dict[str, Any]) -> int:
        """
        Processes Alpha Vantage price data (e.g., from TIME_SERIES_DAILY).
        Returns the number of new PriceData records created.
        """
        time_series_key = next((k for k in raw_data if "Time Series" in k or "Monthly" in k or "Weekly" in k or "Daily" in k), None)
        if not time_series_key or not isinstance(raw_data.get(time_series_key), dict):
            self.logger.warning(f"No valid time series data found in Alpha Vantage response for {commodity.symbol}. Keys: {list(raw_data.keys())}")
            return 0

        time_series = raw_data[time_series_key]
        parsed_items_for_db = []

        for date_str, price_point_data in time_series.items():
            timestamp = self.date_helper.parse_date_string(date_str)
            if not timestamp:
                self.logger.warning(f"Could not parse date string '{date_str}' for {commodity.symbol} from Alpha Vantage. Skipping.")
                continue

            # Alpha Vantage keys are like '1. open', '2. high', etc.
            # Standardize these to match PriceData model fields.
            item_data = {
                'timestamp': timestamp,
                'open_price': self.price_converter.to_decimal(price_point_data.get(next((k for k in price_point_data if 'open' in k.lower()), None))),
                'high_price': self.price_converter.to_decimal(price_point_data.get(next((k for k in price_point_data if 'high' in k.lower()), None))),
                'low_price': self.price_converter.to_decimal(price_point_data.get(next((k for k in price_point_data if 'low' in k.lower()), None))),
                'close_price': self.price_converter.to_decimal(price_point_data.get(next((k for k in price_point_data if 'close' in k.lower()), None))),
                'volume': self.price_converter.to_decimal(price_point_data.get(next((k for k in price_point_data if 'volume' in k.lower()), None))), # Volume can be decimal
                'source_data': price_point_data # Store raw snippet
            }
            # Convert volume to int if it's a Decimal and whole number, or handle as needed
            if isinstance(item_data['volume'], Decimal):
                 item_data['volume'] = int(item_data['volume']) if item_data['volume'] == item_data['volume'].to_integral_value() else None


            if item_data['close_price'] is not None:
                parsed_items_for_db.append(item_data)
            else:
                self.logger.warning(f"Missing or invalid close price for {commodity.symbol} on {date_str} from Alpha Vantage. Data: {price_point_data}")

        if not parsed_items_for_db:
            return 0

        price_data_objects = self._prepare_price_data_entries(commodity, parsed_items_for_db)
        return self._bulk_create_price_data(commodity, price_data_objects)

    def process_fred_data(self, commodity: Commodity, raw_data: Dict[str, Any]) -> int:
        """
        Processes FRED price data from the 'observations' list.
        Returns the number of new PriceData records created.
        """
        if not raw_data or 'observations' not in raw_data or not isinstance(raw_data['observations'], list):
            self.logger.warning(f"No valid 'observations' data found in FRED response for {commodity.symbol}.")
            return 0

        observations = raw_data['observations']
        parsed_items_for_db = []

        for obs in observations:
            value_str = obs.get('value')
            if value_str is None or str(value_str).strip() == '.': # FRED uses '.' for missing values
                self.logger.debug(f"Skipping FRED observation for {commodity.symbol} due to missing/invalid value on date {obs.get('date')}.")
                continue

            timestamp = self.date_helper.parse_date_string(obs.get('date'))
            if not timestamp:
                self.logger.warning(f"Could not parse date string '{obs.get('date')}' for {commodity.symbol} from FRED. Skipping.")
                continue

            close_price = self.price_converter.to_decimal(value_str)
            if close_price is None:
                self.logger.warning(f"Could not convert value '{value_str}' to Decimal for {commodity.symbol} on {obs.get('date')} from FRED. Skipping.")
                continue

            # FRED data typically only provides a single value (interpreted as close_price)
            item_data = {
                'timestamp': timestamp,
                'close_price': close_price,
                'source_data': obs # Store raw snippet
                # open, high, low, volume are typically not available directly from FRED observations for price series.
            }
            parsed_items_for_db.append(item_data)

        if not parsed_items_for_db:
            return 0

        price_data_objects = self._prepare_price_data_entries(commodity, parsed_items_for_db)
        return self._bulk_create_price_data(commodity, price_data_objects)


class MarketUpdateOrchestrationService:
    """
    Service for managing the overall market data update process, including logging.
    It uses CommodityDataFetcherOrchestrator to get data and PriceDataProcessor to save it.
    """
    def __init__(self):
        self.data_fetcher = CommodityDataFetcherOrchestrator()
        self.price_processor = PriceDataProcessor()
        self.logger = logging.getLogger(f"apps.{self.__class__.__module__}.{self.__class__.__name__}")

    def _get_processor_method_for_source(self, source_name: str):
        """Helper to get the correct PriceDataProcessor method for a given source name."""
        source_name_lower = source_name.lower()
        if source_name_lower == 'alpha vantage':
            return self.price_processor.process_alpha_vantage_data
        elif source_name_lower == 'fred':
            return self.price_processor.process_fred_data
        # Add other sources here
        # elif source_name_lower == 'another_api':
        #     return self.price_processor.process_another_api_data
        else:
            self.logger.warning(f"No specific data processing method found for source: {source_name}")
            return None


    def update_single_commodity(self, commodity: Commodity, task_id: Optional[str] = None, **fetch_kwargs) -> Tuple[bool, str, int]:
        """
        Updates price data for a single commodity.
        Creates and manages a MarketUpdate log entry.
        Returns a tuple: (success_bool, message_str, records_created_int).
        `fetch_kwargs` are passed to the data_fetcher.
        """
        self.logger.info(f"Starting price update for commodity: {commodity.symbol} (ID: {commodity.id}), Task ID: {task_id}")
        update_log = MarketUpdate.objects.create(
            data_source=commodity.data_source,
            commodity=commodity,
            status='PENDING',
            task_id=task_id
        )
        update_log.mark_as_running(task_id=task_id) # Also sets started_at

        records_created = 0
        success = False
        message = ""

        try:
            raw_data = self.data_fetcher.fetch_data_for_commodity(commodity, **fetch_kwargs)
            
            if raw_data:
                # Estimate records fetched (crude estimation based on source)
                num_fetched = self._estimate_records_in_raw_data(raw_data, commodity.data_source.name)
                update_log.records_fetched = num_fetched
                # update_log.save(update_fields=['records_fetched']) # Save immediately or with mark_as_completed

                processor_method = self._get_processor_method_for_source(commodity.data_source.name)
                if processor_method:
                    records_created = processor_method(commodity, raw_data)
                    if records_created > 0:
                        message = f"Successfully created {records_created} new price records for {commodity.symbol}."
                        update_log.mark_as_completed(status='SUCCESS', records_fetched=num_fetched, records_created=records_created)
                        success = True
                    else:
                        message = f"Data fetched for {commodity.symbol}, but no new price records were created (data might be old, malformed, or already exist)."
                        update_log.mark_as_completed(status='PARTIAL', records_fetched=num_fetched, records_created=0, error_message=message)
                        # success remains False or could be True depending on definition of "partial success"
                else:
                    message = f"No data processor available for source '{commodity.data_source.name}' for commodity {commodity.symbol}."
                    update_log.mark_as_completed(status='FAILED', records_fetched=num_fetched, error_message=message)
            else:
                message = f"No data received from {commodity.data_source.name} for {commodity.symbol}."
                update_log.mark_as_completed(status='FAILED', error_message=message)

        except (APIKeyMissingError, ConfigurationError) as config_err:
            message = f"Configuration error for {commodity.data_source.name} updating {commodity.symbol}: {config_err}"
            self.logger.error(message)
            update_log.mark_as_completed(status='FAILED', error_message=str(config_err))
        except RateLimitExceededError as rl_err:
            message = f"Rate limit exceeded for {commodity.data_source.name} updating {commodity.symbol}: {rl_err}"
            self.logger.warning(message) # Warning as it's an API constraint
            update_log.mark_as_completed(status='FAILED', error_message=str(rl_err))
        except DataFetchError as df_err:
            message = f"Data fetch error for {commodity.symbol} from {commodity.data_source.name}: {df_err}"
            self.logger.error(message)
            update_log.mark_as_completed(status='FAILED', error_message=str(df_err))
        except DataProcessingError as dp_err:
            message = f"Data processing error for {commodity.symbol}: {dp_err}"
            self.logger.error(message)
            update_log.mark_as_completed(status='FAILED', error_message=str(dp_err))
        except Exception as e:
            message = f"An unexpected error occurred updating {commodity.symbol}: {e}"
            self.logger.exception(message) # Logs full traceback
            update_log.mark_as_completed(status='FAILED', error_message=str(e))
            # For Celery, re-raising might be desired to mark task as FAILED explicitly
            # raise
        
        self.logger.info(f"Completed update for {commodity.symbol}. Success: {success}, Message: {message}, New Records: {records_created}")
        return success, message, records_created

    def _estimate_records_in_raw_data(self, raw_data: Dict[str, Any], source_name: str) -> int:
        """Helper to estimate number of primary records in raw data based on source conventions."""
        try:
            source_name_lower = source_name.lower()
            if source_name_lower == 'alpha vantage':
                # Find a key that looks like a time series
                time_series_key = next((k for k in raw_data if "Time Series" in k or "Monthly" in k or "Weekly" in k or "Daily" in k), None)
                if time_series_key and isinstance(raw_data.get(time_series_key), dict):
                    return len(raw_data[time_series_key])
            elif source_name_lower == 'fred':
                if 'observations' in raw_data and isinstance(raw_data['observations'], list):
                    return len(raw_data['observations'])
        except Exception:
            self.logger.warning(f"Could not estimate records from raw_data for source {source_name}.", exc_info=True)
        return 0 # Default if estimation fails or source unknown 