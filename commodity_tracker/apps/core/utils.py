"""
Utility functions for the application.
"""
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta # Ensure timedelta is imported
from django.utils import timezone

logger = logging.getLogger(__name__) # Define logger at module level


class PriceConverter:
    """Utility class for price conversions and formatting."""

    @staticmethod
    def to_decimal(value: any, default: Decimal = None) -> Decimal | None:
        """
        Convert a value to Decimal safely.
        Handles None, empty strings, and conversion errors.
        """
        if value is None or str(value).strip() == '':
            return default
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            logger.warning(f"Could not convert value '{value}' (type: {type(value)}) to Decimal.")
            return default

    @staticmethod
    def format_price(price: Decimal | None, currency: str = 'USD', decimal_places: int = 2) -> str:
        """Format price with currency symbol and specified decimal places."""
        if price is None:
            return 'N/A'
        format_string = "{:,.%df}" % decimal_places
        return f"{currency} {format_string.format(price)}"


class DateTimeHelper:
    """Utility class for datetime operations."""

    @staticmethod
    def parse_date_string(date_str: str, format_str: str = '%Y-%m-%d') -> datetime | None:
        """
        Parse a date string to a timezone-aware datetime object (UTC).
        Returns None if parsing fails.
        """
        if not date_str:
            return None
        try:
            dt_naive = datetime.strptime(date_str, format_str)
            return timezone.make_aware(dt_naive, timezone.utc) # Assume UTC if naive
        except ValueError as e:
            logger.error(f"Error parsing date string '{date_str}' with format '{format_str}': {e}")
            return None

    @staticmethod
    def get_days_ago(days: int) -> datetime:
        """Get a timezone-aware datetime object for a number of days ago from now."""
        return timezone.now() - timedelta(days=days)

    @staticmethod
    def datetime_to_string(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str | None:
        """Convert a datetime object to a string."""
        if not dt:
            return None
        return dt.strftime(format_str) 