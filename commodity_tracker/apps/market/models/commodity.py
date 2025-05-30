"""
Commodity-related models: DataSource, CommodityCategory, and Commodity.
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta
from .base import TimeStampedModel, UUIDModel, ActiveModel
from ..managers.commodity_managers import CommodityManager, ActiveCommodityManager
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


class DataSource(TimeStampedModel, ActiveModel):
    """Model representing data sources for commodity information (e.g., APIs)."""
    name = models.CharField(max_length=100, unique=True, help_text="Name of the data source (e.g., Alpha Vantage, FRED).")
    description = models.TextField(blank=True, help_text="Optional description for the data source.")
    base_url = models.URLField(max_length=255, help_text="Base URL for the API, if applicable.")
    api_key_required = models.BooleanField(default=True, help_text="Does this data source require an API key?")
    rate_limit_per_minute = models.PositiveIntegerField(
        default=5,
        null=True, blank=True, # Can be null if not applicable or unknown
        help_text="Informational: Approximate rate limit per minute. Actual enforcement is in service layer."
    )
    api_key = models.CharField(max_length=255, blank=True, help_text="API key for the data source, if required.")

    class Meta(TimeStampedModel.Meta): # Inherit ordering from TimeStampedModel
        db_table = 'market_data_source'
        verbose_name = "Data Source"
        verbose_name_plural = "Data Sources"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.base_url and not self.base_url.startswith(('http://', 'https://')):
            raise ValidationError({'base_url': "URL must start with 'http://' or 'https://'."})


class CommodityCategory(TimeStampedModel):
    """Model representing categories for commodities (e.g., Energy, Metals, Grains)."""
    name = models.CharField(max_length=100, unique=True, help_text="Name of the commodity category.")
    description = models.TextField(blank=True, help_text="Optional description for the category.")

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Commodity Category"
        verbose_name_plural = "Commodity Categories"
        db_table = 'market_commodity_category'

    def __str__(self):
        return self.name

    def get_commodities_count(self) -> int:
        """Returns the count of active commodities in this category."""
        return self.commodities.filter(is_active=True).count()


class Commodity(UUIDModel, TimeStampedModel, ActiveModel):
    """Model representing a tradable commodity."""
    name = models.CharField(max_length=200, help_text="Full name of the commodity (e.g., Crude Oil, Gold, Corn).")
    symbol = models.CharField(max_length=50, unique=True, help_text="Unique trading symbol or ticker for the commodity.") # Increased length
    description = models.TextField(blank=True, help_text="Optional description for the commodity.")
    category = models.ForeignKey(
        CommodityCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True, # Category can be optional
        related_name='commodities',
        help_text="Category this commodity belongs to."
    )
    exchange = models.CharField(max_length=100, blank=True, help_text="Exchange where this commodity is primarily traded (e.g., NYMEX, COMEX).")
    unit = models.CharField(max_length=50, blank=True, help_text="Unit of measurement for the commodity's price (e.g., Barrel, Ounce, Bushel).")
    currency = models.CharField(max_length=10, default='USD', help_text="Currency in which the price is denoted (e.g., USD, EUR).") # Increased length
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.PROTECT, # Prevent deleting a data source if commodities are linked to it.
        related_name='commodities',
        help_text="Primary data source for this commodity's price information."
    )
    external_id = models.CharField(
        max_length=100,
        help_text="ID used by the external data source (e.g., specific symbol for Alpha Vantage, series ID for FRED)."
    )
    meta_data = models.JSONField(default=dict, blank=True, help_text="Optional JSON field for storing additional metadata about the commodity.")
    last_updated = models.DateTimeField(null=True, blank=True, help_text="Last updated date and time of the commodity's data.")
    update_frequency_minutes = models.IntegerField(default=60, validators=[MinValueValidator(1)], help_text="Update frequency in minutes.")

    # Custom managers
    objects = CommodityManager()  # Default manager
    active = ActiveCommodityManager()  # Manager for active_only commodities

    class Meta(TimeStampedModel.Meta, UUIDModel.Meta): # Inherit ordering and ensure UUIDModel Meta is also considered
        indexes = [
            models.Index(fields=['symbol']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['data_source', 'external_id']),
            models.Index(fields=['name']), # Index on name for searching
        ]
        unique_together = [['data_source', 'external_id']] # External ID should be unique per data source
        db_table = 'market_commodity'
        verbose_name = "Commodity"
        verbose_name_plural = "Commodities"
        ordering = ['symbol']

    def __str__(self):
        return f"{self.name} ({self.symbol})"

    def get_latest_price(self) -> 'PriceData | None':
        """Get the most recent PriceData point for this commodity."""
        return self.prices.order_by('-timestamp').first()

    def get_price_history(self, days: int = 30) -> models.QuerySet['PriceData']:
        """Get price history for the specified number of days, ordered chronologically."""
        start_date = timezone.now() - timedelta(days=days)
        return self.prices.filter(timestamp__gte=start_date).order_by('timestamp')

    def has_recent_data(self, hours: int = 24) -> bool:
        """Check if the commodity has price data within the recent specified hours."""
        cutoff = timezone.now() - timedelta(hours=hours)
        return self.prices.filter(timestamp__gte=cutoff).exists()

    def clean(self):
        super().clean()
        # Example validation: Ensure symbol is uppercase if that's a convention
        if self.symbol:
            self.symbol = self.symbol.upper()

    def activate(self):
        self.is_active = True
        self.save()

    def deactivate(self):
        self.is_active = False
        self.save()

    def update_last_updated(self):
        self.last_updated = timezone.now()
        self.save() 