"""
Signal handlers for the market app.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Commodity, PriceData, MarketUpdate


@receiver(pre_save, sender=Commodity)
def commodity_pre_save(sender, instance, **kwargs):
    """
    Handle pre-save signals for Commodity model.
    """
    # Ensure symbol is uppercase
    if instance.symbol:
        instance.symbol = instance.symbol.upper()
    
    # Ensure exchange name is properly formatted
    if instance.exchange:
        instance.exchange = instance.exchange.strip().title()


@receiver(post_save, sender=PriceData)
def price_data_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save signals for PriceData model.
    """
    if created:
        # Update the commodity's last_updated field
        commodity = instance.commodity
        commodity.last_updated = instance.timestamp
        commodity.save(update_fields=['last_updated'])


@receiver(post_save, sender=MarketUpdate)
def market_update_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save signals for MarketUpdate model.
    """
    if created:
        # Set started_at when a new update is created
        instance.started_at = timezone.now()
        instance.save(update_fields=['started_at'])
    
    # If the update is being marked as completed
    if instance.status == MarketUpdate.STATUS_COMPLETED and not instance.completed_at:
        instance.completed_at = timezone.now()
        instance.save(update_fields=['completed_at']) 