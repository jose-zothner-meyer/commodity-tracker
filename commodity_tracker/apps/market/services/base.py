"""
Base service classes for data fetching and API interaction.
"""
import logging
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from apps.core.exceptions import DataFetchError, APIKeyMissingError, ConfigurationError

class BaseDataService(ABC):
    """Abstract base class for services that fetch and process data."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key  # Specific API key for this service instance, if passed directly
        self.logger = logging.getLogger(f"apps.{self.__class__.__module__}.{self.__class__.__name__}")

    @abstractmethod
    def fetch_data(self, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """Fetches data from an external source."""
        pass

    @abstractmethod
    def process_data(self, data: Dict[str, Any], *args, **kwargs) -> int:
        """
        Processes fetched data.
        Should return a count, e.g., number of records created or processed.
        """
        pass

    def validate_api_key_is_present(self) -> None:
        """Validates that an API key is available for the service if it's required."""
        # This method is more for services that might receive an API key dynamically.
        # Clients like AlphaVantageClient usually get keys from Django settings.
        if not self.api_key:
            raise APIKeyMissingError(f"An API key is required for {self.__class__.__name__} but was not provided.")

    def handle_service_error(self, error: Exception, context: str = "", raise_as: Exception = DataFetchError) -> None:
        """Handles errors consistently within the service."""
        error_msg = f"Error in {self.__class__.__name__} during {context}: {str(error)}"
        self.logger.error(error_msg, exc_info=True)  # Log with full traceback
        raise raise_as(error_msg) from error

class BaseAPIClient(ABC):
    """Abstract base class for HTTP API clients."""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        if not base_url:
            raise ConfigurationError(f"{self.__class__.__name__} requires a base_url.")
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key  # API key specific to this client instance
        self.timeout = timeout
        self._session = None  # Use a private attribute for the session
        self.logger = logging.getLogger(f"apps.{self.__class__.__module__}.{self.__class__.__name__}")

    @property
    def session(self) -> requests.Session:
        """Provides a requests.Session instance, creating it if it doesn't exist."""
        if self._session is None:
            self._session = requests.Session()
            # Example: Set a default User-Agent header
            self._session.headers.update({
                'User-Agent': f'CommodityTrackerApp/1.0 ({self.__class__.__name__})'
            })
        return self._session

    @abstractmethod
    def build_request_params(self, **kwargs) -> Dict[str, Any]:
        """Builds the dictionary of parameters for an API request."""
        pass

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None,
                     json_data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Internal method to make an HTTP request to the API.
        Handles common request logic and error handling.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = self.session.headers.copy()  # Start with session headers
        if headers:
            request_headers.update(headers)

        self.logger.debug(f"Making {method.upper()} request to {url} with params: {params}, json: {json_data}")

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=request_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error occurred: {str(e)}")
            raise DataFetchError(f"HTTP error occurred: {str(e)}") from e
        except requests.exceptions.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON response: {str(e)}")
            raise DataFetchError(f"Failed to decode JSON response: {str(e)}") from e
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            raise DataFetchError(f"Request failed: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Unexpected error occurred: {str(e)}")
            raise DataFetchError(f"Unexpected error occurred: {str(e)}") from e

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Makes a GET request to the API."""
        return self._make_request('GET', endpoint, params=params, headers=headers)

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Makes a POST request to the API."""
        return self._make_request('POST', endpoint, json_data=json_data, headers=headers)

    def put(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Makes a PUT request to the API."""
        return self._make_request('PUT', endpoint, json_data=json_data, headers=headers)

    def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Makes a DELETE request to the API."""
        return self._make_request('DELETE', endpoint, params=params, headers=headers) 