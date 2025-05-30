"""
Custom exceptions for the commodity tracker application.
"""

class CommodityTrackerException(Exception):
    """Base exception for commodity tracker application."""
    pass

class DataFetchError(CommodityTrackerException):
    """Raised when data fetching from an external API fails."""
    pass

class DataProcessingError(CommodityTrackerException):
    """Raised when processing fetched data fails."""
    pass

class APIKeyMissingError(CommodityTrackerException):
    """Raised when a required API key is missing from settings."""
    pass

class RateLimitExceededError(CommodityTrackerException):
    """Raised when an API rate limit is believed to have been exceeded."""
    pass

class ConfigurationError(CommodityTrackerException):
    """Raised for application configuration issues."""
    pass 