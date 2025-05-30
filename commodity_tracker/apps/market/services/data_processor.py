"""
Service for processing market data from external sources.
"""
import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from ..models import Commodity, PriceData, MarketUpdate

logger = logging.getLogger(__name__)

class DataProcessor:
    """Service class for processing market data from external sources."""

    def __init__(self, market_update: MarketUpdate):
        self.market_update = market_update
        self.data_source = market_update.data_source
        self.commodity = market_update.commodity

    def process_data(self, raw_data: Dict[str, Any]) -> List[PriceData]:
        """
        Processes raw market data and creates or updates PriceData records.
        
        Args:
            raw_data: Dictionary containing the raw market data.
            
        Returns:
            List of created or updated PriceData instances.
            
        Raises:
            ValueError: If the raw data is invalid or missing required fields.
        """
        try:
            processed_data = self._extract_price_data(raw_data)
            price_data_list = []
            
            for data in processed_data:
                price_data = self._create_or_update_price_data(data)
                if price_data:
                    price_data_list.append(price_data)
            
            return price_data_list
        except Exception as e:
            logger.error(f"Error processing data for {self.data_source.name}: {str(e)}")
            raise

    def _extract_price_data(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts price data from the raw API response."""
        # This is a placeholder implementation. The actual implementation would depend on the API response structure.
        if not isinstance(raw_data, dict):
            raise ValueError("Raw data must be a dictionary.")
        
        # Example: Extract price data from a list of records
        if 'data' in raw_data and isinstance(raw_data['data'], list):
            return raw_data['data']
        
        # Example: Extract price data from a single record
        if all(key in raw_data for key in ['timestamp', 'open', 'high', 'low', 'close']):
            return [raw_data]
        
        raise ValueError("Raw data does not contain valid price data.")

    def _create_or_update_price_data(self, data: Dict[str, Any]) -> Optional[PriceData]:
        """Creates or updates a PriceData record from the processed data."""
        try:
            timestamp = self._parse_timestamp(data['timestamp'])
            
            # Check if a PriceData record already exists for this timestamp
            price_data = PriceData.objects.filter(
                commodity=self.commodity,
                timestamp=timestamp
            ).first()
            
            if price_data:
                # Update existing record
                price_data.open_price = data.get('open')
                price_data.high_price = data.get('high')
                price_data.low_price = data.get('low')
                price_data.close_price = data.get('close')
                price_data.volume = data.get('volume')
                price_data.source_data = data
                price_data.save()
            else:
                # Create new record
                price_data = PriceData.objects.create(
                    commodity=self.commodity,
                    timestamp=timestamp,
                    open_price=data.get('open'),
                    high_price=data.get('high'),
                    low_price=data.get('low'),
                    close_price=data.get('close'),
                    volume=data.get('volume'),
                    source_data=data
                )
            
            return price_data
        except Exception as e:
            logger.error(f"Error creating/updating price data: {str(e)}")
            return None

    def _parse_timestamp(self, timestamp: Any) -> timezone.datetime:
        """Parses the timestamp from the raw data into a timezone-aware datetime."""
        # This is a placeholder implementation. The actual implementation would depend on the API timestamp format.
        if isinstance(timestamp, str):
            # Example: Parse ISO format timestamp
            return timezone.datetime.fromisoformat(timestamp)
        elif isinstance(timestamp, (int, float)):
            # Example: Parse Unix timestamp
            return timezone.datetime.fromtimestamp(timestamp, tz=timezone.utc)
        else:
            raise ValueError(f"Invalid timestamp format: {timestamp}") 