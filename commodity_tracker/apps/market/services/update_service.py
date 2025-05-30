"""
Service for orchestrating market data updates.
"""
import logging
from typing import Optional, List
from django.utils import timezone
from ..models import Commodity, MarketUpdate, PriceData
from .data_fetcher import DataFetcher
from .data_processor import DataProcessor

logger = logging.getLogger(__name__)

class UpdateService:
    """Service class for orchestrating market data updates."""

    def __init__(self, data_source_name: str):
        self.data_source_name = data_source_name
        self.data_fetcher = None
        self.market_update = None

    def update_commodity(self, commodity: Commodity) -> Optional[MarketUpdate]:
        """
        Updates market data for a specific commodity.
        
        Args:
            commodity: The Commodity instance to update.
            
        Returns:
            MarketUpdate instance if successful, None otherwise.
        """
        try:
            # Create a new market update record
            self.market_update = MarketUpdate.objects.create(
                data_source=self.data_source_name,
                commodity=commodity,
                status='in_progress',
                started_at=timezone.now()
            )
            
            # Initialize the data fetcher
            self.data_fetcher = DataFetcher(self.data_source_name)
            
            # Fetch the data
            raw_data = self.data_fetcher.fetch_data(commodity)
            if not raw_data:
                self._mark_update_failed("No data received from data source")
                return None
            
            # Process the data
            processor = DataProcessor(self.market_update)
            price_data_list = processor.process_data(raw_data)
            
            # Update the market update record
            self.market_update.status = 'completed'
            self.market_update.records_fetched = len(raw_data)
            self.market_update.records_created = len(price_data_list)
            self.market_update.completed_at = timezone.now()
            self.market_update.save()
            
            return self.market_update
            
        except Exception as e:
            logger.error(f"Error updating commodity {commodity.symbol}: {str(e)}")
            if self.market_update:
                self._mark_update_failed(str(e))
            return None

    def update_all_commodities(self) -> List[MarketUpdate]:
        """
        Updates market data for all active commodities.
        
        Returns:
            List of MarketUpdate instances for successful updates.
        """
        successful_updates = []
        commodities = Commodity.objects.filter(is_active=True)
        
        for commodity in commodities:
            update = self.update_commodity(commodity)
            if update and update.status == 'completed':
                successful_updates.append(update)
        
        return successful_updates

    def _mark_update_failed(self, error_message: str):
        """Marks the current market update as failed with the given error message."""
        if self.market_update:
            self.market_update.status = 'failed'
            self.market_update.error_message = error_message
            self.market_update.completed_at = timezone.now()
            self.market_update.save() 