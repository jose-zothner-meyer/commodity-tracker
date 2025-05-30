"""
App configuration for the market app.
"""
from django.apps import AppConfig


class MarketConfig(AppConfig):
    """Configuration for the market app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'commodity_tracker.apps.market'
    verbose_name = 'Market Data'
    
    def ready(self):
        """Initialize app when Django starts."""
        try:
            import commodity_tracker.apps.market.signals  # noqa
        except ImportError:
            pass 