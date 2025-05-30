"""
Custom managers and QuerySets for Commodity models.
"""
from django.db import models
from django.db.models import Count, Q # Added Q for more complex queries if needed
from django.utils import timezone
from datetime import timedelta


class CommodityQuerySet(models.QuerySet):
    """Custom QuerySet for the Commodity model."""

    def active(self):
        """Filters for active commodities (is_active=True)."""
        return self.filter(is_active=True)

    def inactive(self):
        """Filters for inactive commodities (is_active=False)."""
        return self.filter(is_active=False)

    def by_category_name(self, category_name: str):
        """Filters commodities by category name (case-insensitive contains)."""
        return self.filter(category__name__icontains=category_name)

    def by_category_id(self, category_id):
        """Filters commodities by category ID."""
        return self.filter(category_id=category_id)

    def with_recent_price_data(self, hours: int = 24):
        """
        Filters commodities that have associated PriceData entries within the last specified hours.
        Uses distinct to avoid duplicates if a commodity has multiple recent prices.
        """
        cutoff_time = timezone.now() - timedelta(hours=hours)
        return self.filter(prices__timestamp__gte=cutoff_time).distinct()

    def without_recent_price_data(self, hours: int = 24):
        """
        Filters commodities that DO NOT have associated PriceData entries within the last specified hours.
        """
        cutoff_time = timezone.now() - timedelta(hours=hours)
        return self.exclude(prices__timestamp__gte=cutoff_time).distinct()

    def by_exchange(self, exchange_name: str):
        """Filters commodities by exchange name (case-insensitive contains)."""
        return self.filter(exchange__icontains=exchange_name)

    def by_data_source(self, data_source_name: str):
        """Filters commodities by data source name."""
        return self.filter(data_source__name__iexact=data_source_name)

    def needs_update(self, hours: int = 24):
        """
        Identifies commodities that might need a price update.
        This could be commodities with no recent data or those not updated recently.
        (This is a basic example; more sophisticated logic might be needed).
        """
        # Commodities that don't have price data in the last `hours`
        return self.without_recent_price_data(hours)


class CommodityManager(models.Manager):
    """Custom manager for the Commodity model."""

    def get_queryset(self):
        return CommodityQuerySet(self.model, using=self._db)

    def active(self):
        """Returns a QuerySet of active commodities."""
        return self.get_queryset().active()

    def inactive(self):
        """Returns a QuerySet of inactive commodities."""
        return self.get_queryset().inactive()

    def by_category_name(self, category_name: str):
        """Returns commodities filtered by category name."""
        return self.get_queryset().by_category_name(category_name)

    def with_recent_price_data(self, hours: int = 24):
        """Returns commodities with recent price data."""
        return self.get_queryset().with_recent_price_data(hours)

    def get_popular_commodities(self, limit: int = 10):
        """
        Gets popular commodities.
        Popularity can be defined in various ways, e.g., by the number of recent price updates
        or by the number of times they've been part of a MarketUpdate log.
        This example uses the count of associated PriceData entries.
        """
        return (
            self.active()
            .annotate(price_data_count=Count('prices'))
            .order_by('-price_data_count', 'name')[:limit]
        )

    def get_commodities_for_update(self, hours_since_last_data: int = 24):
        """Gets commodities that likely need a price data update."""
        return self.get_queryset().needs_update(hours=hours_since_last_data)


class ActiveCommodityManager(models.Manager):
    """A manager that returns only active (is_active=True) commodities by default."""

    def get_queryset(self):
        # Calls the custom CommodityQuerySet and filters for active items.
        return CommodityQuerySet(self.model, using=self._db).active()

    # You can add other methods here that should also operate only on active commodities.
    # For example:
    # def by_category_name(self, category_name: str):
    #     return self.get_queryset().by_category_name(category_name) 