"""
Data fetching services for different external APIs (Alpha Vantage, FRED, etc.).
These services are responsible for making HTTP requests and handling API-specific responses.
"""
import logging
from typing import Dict, Any, Optional, List
from django.conf import settings
from .base import BaseAPIClient
from apps.core.exceptions import DataFetchError, RateLimitExceededError, APIKeyMissingError, ConfigurationError
from apps.market.models import Commodity

logger = logging.getLogger(__name__)

class AlphaVantageClient(BaseAPIClient):
    """API client for Alpha Vantage."""

    DEFAULT_BASE_URL = "https://www.alphavantage.co"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        resolved_api_key = api_key or settings.ALPHA_VANTAGE_API_KEY
        if not resolved_api_key:
            raise APIKeyMissingError("Alpha Vantage API key (ALPHA_VANTAGE_API_KEY) not found in settings or provided.")
        super().__init__(
            base_url=base_url or self.DEFAULT_BASE_URL,
            api_key=resolved_api_key
        )

    def build_request_params(self, function: str, symbol: str, **kwargs) -> Dict[str, Any]:
        """Builds request parameters common to many Alpha Vantage functions."""
        params = {
            'function': function,
            'symbol': symbol,
            'apikey': self.api_key,
        }
        # Add common optional parameters
        if 'interval' in kwargs: params['interval'] = kwargs['interval']
        if 'outputsize' in kwargs: params['outputsize'] = kwargs['outputsize'] # 'compact' or 'full'
        if 'datatype' in kwargs: params['datatype'] = kwargs['datatype'] # 'json' or 'csv'
        return params

    def fetch_time_series_daily(self, symbol: str, outputsize: str = 'compact') -> Dict[str, Any]:
        """Fetches TIME_SERIES_DAILY_ADJUSTED data."""
        params = self.build_request_params(
            function='TIME_SERIES_DAILY_ADJUSTED', # Using adjusted as it's often more useful
            symbol=symbol,
            outputsize=outputsize
        )
        self.logger.info(f"Fetching Alpha Vantage TIME_SERIES_DAILY for symbol: {symbol}")
        data = self.get('query', params=params)
        return self._handle_alpha_vantage_response(data, symbol)

    def _handle_alpha_vantage_response(self, data: Dict[str, Any], request_identifier: str) -> Dict[str, Any]:
        """Handles common Alpha Vantage API response patterns (errors, notes)."""
        if not data:
            self.logger.warning(f"Empty response from Alpha Vantage for {request_identifier}.")
            return {} # Or raise DataFetchError("Empty response")

        if 'Error Message' in data:
            error_msg = data['Error Message']
            self.logger.error(f"Alpha Vantage API error for {request_identifier}: {error_msg}")
            raise DataFetchError(f"Alpha Vantage API error: {error_msg}")

        # Alpha Vantage often includes rate limit notes or informational messages
        note = data.get('Note') or data.get('Information')
        if note:
            self.logger.warning(f"Alpha Vantage API note for {request_identifier}: {note}")
            # Basic check for rate limit message (these messages can vary)
            if "call frequency" in note.lower() or "premium endpoint" in note.lower():
                raise RateLimitExceededError(f"Alpha Vantage rate limit likely exceeded or premium endpoint hit: {note}")
        return data


class FREDClient(BaseAPIClient):
    """API client for FRED (Federal Reserve Economic Data)."""

    DEFAULT_BASE_URL = "https://api.stlouisfed.org/fred"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        resolved_api_key = api_key or settings.FRED_API_KEY
        if not resolved_api_key:
            raise APIKeyMissingError("FRED API key (FRED_API_KEY) not found in settings or provided.")
        super().__init__(
            base_url=base_url or self.DEFAULT_BASE_URL,
            api_key=resolved_api_key
        )

    def build_request_params(self, series_id: str, **kwargs) -> Dict[str, Any]:
        """Builds request parameters for FRED series observations."""
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json', # Always request JSON
        }
        # Common optional parameters for /series/observations
        if 'limit' in kwargs: params['limit'] = kwargs['limit'] # Max 100000 if allowed, default 1000
        if 'sort_order' in kwargs: params['sort_order'] = kwargs['sort_order'] # 'asc' or 'desc'
        if 'observation_start' in kwargs: params['observation_start'] = kwargs['observation_start'] # YYYY-MM-DD
        if 'observation_end' in kwargs: params['observation_end'] = kwargs['observation_end'] # YYYY-MM-DD
        if 'units' in kwargs: params['units'] = kwargs['units'] # e.g., 'lin' (levels), 'chg' (change)
        if 'frequency' in kwargs: params['frequency'] = kwargs['frequency'] # e.g., 'd', 'w', 'm', 'q', 'a'
        return params

    def fetch_series_observations(self, series_id: str, **kwargs) -> Dict[str, Any]:
        """Fetches observations for a given FRED series ID."""
        params = self.build_request_params(series_id, **kwargs)
        self.logger.info(f"Fetching FRED series observations for series_id: {series_id}")
        data = self.get('series/observations', params=params)
        return self._handle_fred_response(data, series_id)

    def _handle_fred_response(self, data: Dict[str, Any], request_identifier: str) -> Dict[str, Any]:
        """Handles common FRED API response patterns."""
        if not data:
            self.logger.warning(f"Empty response from FRED for {request_identifier}.")
            return {}

        # FRED API errors are usually in the response body with an error_code or message
        error_code = data.get('error_code')
        error_message = data.get('error_message')
        if error_code or error_message:
            full_error_msg = error_message or f"FRED API error code: {error_code}"
            self.logger.error(f"FRED API error for {request_identifier}: {full_error_msg}")
            # Check for common rate limit error codes if known (e.g., 429 is a common HTTP status for rate limits)
            # FRED's specific error codes for rate limits would need to be identified from their docs.
            if error_code == 429 or "rate limit" in (error_message or "").lower():
                 raise RateLimitExceededError(f"FRED rate limit likely exceeded: {full_error_msg}")
            raise DataFetchError(full_error_msg)
        return data


class CommodityDataFetcherOrchestrator(BaseAPIClient):
    """
    Orchestrates data fetching from different sources based on the commodity's configuration.
    This class acts as a facade for the different API clients, providing a unified interface
    for fetching commodity data regardless of the source.
    """
    def __init__(self):
        super().__init__(base_url="")  # No base URL needed for orchestrator
        self._clients = {}  # Cache for API clients

    def _get_client_for_source(self, source_name: str) -> BaseAPIClient:
        """Gets or creates the appropriate API client for a given source."""
        source_name_lower = source_name.lower()
        if source_name_lower not in self._clients:
            if source_name_lower == 'alpha vantage':
                self._clients[source_name_lower] = AlphaVantageClient()
            elif source_name_lower == 'fred':
                self._clients[source_name_lower] = FREDClient()
            else:
                raise ConfigurationError(f"No API client configured for source: {source_name}")
        return self._clients[source_name_lower]

    def fetch_data_for_commodity(self, commodity: Commodity, **kwargs) -> Dict[str, Any]:
        """
        Fetches data for a commodity using its configured data source.
        
        Args:
            commodity: The Commodity instance to fetch data for.
            **kwargs: Additional parameters to pass to the specific API client.
            
        Returns:
            Dictionary containing the fetched data.
            
        Raises:
            ConfigurationError: If the commodity's data source is not supported.
            DataFetchError: If there's an error fetching the data.
        """
        try:
            client = self._get_client_for_source(commodity.data_source.name)
            
            # Map commodity configuration to API-specific parameters
            if isinstance(client, AlphaVantageClient):
                return client.fetch_time_series_daily(
                    symbol=commodity.symbol,
                    outputsize=kwargs.get('outputsize', 'compact')
                )
            elif isinstance(client, FREDClient):
                return client.fetch_series_observations(
                    series_id=commodity.symbol,
                    **kwargs
                )
            else:
                raise ConfigurationError(f"Unsupported data source: {commodity.data_source.name}")
                
        except Exception as e:
            self.logger.error(f"Error fetching data for {commodity.symbol}: {str(e)}")
            raise DataFetchError(f"Failed to fetch data for {commodity.symbol}: {str(e)}") from e 