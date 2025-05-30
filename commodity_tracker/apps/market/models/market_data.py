"""
Market data models: PriceData (for individual price points) and MarketUpdate (for logging data fetch operations).
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from .base import TimeStampedModel
from .commodity import Commodity, DataSource # DataSource for MarketUpdate FK


class PriceData(TimeStampedModel):
    """Model representing a single price data point for a commodity at a specific time."""
    commodity = models.ForeignKey(
        Commodity,
        on_delete=models.CASCADE, # If commodity is deleted, its price data is also deleted.
        related_name='prices',
        help_text="The commodity this price data belongs to."
    )
    timestamp = models.DateTimeField(help_text="The specific date and time for this price data point (usually UTC).")
    open_price = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True, help_text="Opening price.") # Increased precision
    high_price = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True, help_text="Highest price during the period.")
    low_price = models.DecimalField(max_digits=15, decimal_places=6, null=True, blank=True, help_text="Lowest price during the period.")
    close_price = models.DecimalField(max_digits=15, decimal_places=6, help_text="Closing price.") # Assuming close price is mandatory
    volume = models.BigIntegerField(null=True, blank=True, help_text="Trading volume during the period.")
    adjusted_close = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True, help_text="Adjusted closing price.")
    dividend_amount = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True, help_text="Dividend amount.")
    split_coefficient = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True, help_text="Split coefficient.")
    source_data = models.JSONField(default=dict, blank=True, help_text="Raw data snippet from the source for this price point, for auditing or reprocessing.")


    class Meta(TimeStampedModel.Meta):
        unique_together = ['commodity', 'timestamp'] # Each commodity can only have one price point per timestamp
        indexes = [
            # unique_together implies an index, but explicit definition can be clearer or allow more options
            models.Index(fields=['commodity', 'timestamp'], name='market_pricedata_com_time_idx'),
            models.Index(fields=['timestamp'], name='market_pricedata_time_idx'), # For querying by time across commodities
        ]
        # Default ordering: latest prices first, then by commodity symbol
        ordering = ['-timestamp', 'commodity__symbol']
        db_table = 'market_price_data'
        verbose_name = "Price Data"
        verbose_name_plural = "Price Data"

    def __str__(self):
        commodity_symbol = self.commodity.symbol if self.commodity else 'N/A'
        return (f"{commodity_symbol} @ {self.timestamp.strftime('%Y-%m-%d %H:%M')} - "
                f"Close: {self.close_price} {self.commodity.currency if self.commodity else ''}")

    @property
    def price_change(self) -> models.Decimal | None:
        """Calculates the absolute price change from open to close. Returns Decimal or None."""
        if self.open_price is not None and self.close_price is not None:
            return self.close_price - self.open_price
        return None

    @property
    def price_change_percentage(self) -> models.Decimal | None:
        """Calculates the percentage price change from open. Returns Decimal or None."""
        change = self.price_change
        if change is not None and self.open_price is not None and self.open_price != 0:
            return (change / self.open_price) * 100
        return None

    def clean(self):
        if self.close_price is not None and self.close_price < 0:
            raise MinValueValidator({'close_price': 'Close price cannot be negative'})
        if self.volume is not None and self.volume < 0:
            raise MinValueValidator({'volume': 'Volume cannot be negative'})


class MarketUpdate(TimeStampedModel, models.Model): # Explicitly inherit from models.Model for UUID pk if needed, or use UUIDModel
    """Model representing a log of market data update operations (e.g., fetching data from an API)."""
    id = models.UUIDField(primary_key=True, default=models.UUIDField().default, editable=False) # Explicit UUID PK

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PARTIAL', 'Partial Success'), # If some records updated but errors occurred
    ]

    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE, # Or PROTECT if logs are critical even if source is deleted
        related_name='update_logs', # Changed related_name for clarity
        help_text="The data source used for this update operation."
    )
    commodity = models.ForeignKey(
        Commodity,
        on_delete=models.CASCADE, # Or PROTECT
        null=True,
        blank=True, # If the update is for the entire data source, not a specific commodity
        related_name='update_logs', # Changed related_name
        help_text="Specific commodity updated, if applicable."
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', help_text="Current status of the update operation.")
    task_id = models.CharField(max_length=255, null=True, blank=True, help_text="Celery task ID, if applicable.")
    records_fetched = models.PositiveIntegerField(default=0, help_text="Number of raw records/data points fetched from the API.")
    records_created = models.PositiveIntegerField(default=0, help_text="Number of new PriceData records created in the database.")
    records_updated = models.PositiveIntegerField(default=0, help_text="Number of existing PriceData records updated (if applicable).")
    error_message = models.TextField(blank=True, null=True, help_text="Error message if the update operation failed or had issues.")
    started_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the update operation started.")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the update operation completed.")

    class Meta(TimeStampedModel.Meta):
        # Default ordering: latest started updates first
        ordering = ['-started_at', '-created_at']
        db_table = 'market_update_log'
        verbose_name = "Market Update Log"
        verbose_name_plural = "Market Update Logs"

    def __str__(self):
        commodity_info = f" - {self.commodity.symbol}" if self.commodity else " (Source Level)"
        source_name = self.data_source.name if self.data_source else "N/A"
        start_time = (self.started_at or self.created_at).strftime('%Y-%m-%d %H:%M')
        return f"Update Log {self.id_short()}: {source_name}{commodity_info} - {self.status} @ {start_time}"

    def id_short(self):
        return str(self.id).split('-')[0] # Short version of UUID for display

    def mark_as_running(self, task_id=None):
        """Sets the status to RUNNING and records the start time."""
        self.status = 'RUNNING'
        self.started_at = timezone.now()
        if task_id:
            self.task_id = task_id
        self.save(update_fields=['status', 'started_at', 'task_id'] if task_id else ['status', 'started_at'])

    def mark_completed(self, records_fetched=0, records_created=0, records_updated=0):
        """Marks the update as completed with the given status and details."""
        self.status = 'SUCCESS'
        self.completed_at = timezone.now()
        self.records_fetched = records_fetched
        self.records_created = records_created
        self.records_updated = records_updated
        self.save(update_fields=['status', 'completed_at', 'records_fetched', 'records_created', 'records_updated'])

    def mark_failed(self, error_message):
        """Marks the update as failed with the given error message."""
        self.status = 'FAILED'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])

    @property
    def duration(self):
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None 