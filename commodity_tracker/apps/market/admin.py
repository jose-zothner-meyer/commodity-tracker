"""
Admin configuration for the market app.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    DataSource,
    CommodityCategory,
    Commodity,
    PriceData,
    MarketUpdate
)


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    """Admin configuration for DataSource model."""
    
    list_display = ('name', 'base_url', 'api_key_required', 'rate_limit_per_minute')
    list_filter = ('api_key_required',)
    search_fields = ('name', 'base_url')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'base_url')
        }),
        ('API Configuration', {
            'fields': ('api_key_required', 'rate_limit_per_minute')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(CommodityCategory)
class CommodityCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for CommodityCategory model."""
    
    list_display = ('name', 'description', 'active_commodities_count')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    
    def active_commodities_count(self, obj):
        """Display count of active commodities in this category."""
        return obj.active_commodities_count()
    active_commodities_count.short_description = 'Active Commodities'


@admin.register(Commodity)
class CommodityAdmin(admin.ModelAdmin):
    """Admin configuration for Commodity model."""
    
    list_display = ('name', 'symbol', 'category', 'exchange', 'data_source', 'is_active')
    list_filter = ('category', 'data_source', 'is_active', 'currency')
    search_fields = ('name', 'symbol', 'exchange')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'symbol', 'category')
        }),
        ('Market Information', {
            'fields': ('exchange', 'unit', 'currency', 'data_source')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(PriceData)
class PriceDataAdmin(admin.ModelAdmin):
    """Admin configuration for PriceData model."""
    
    list_display = ('commodity', 'timestamp', 'close_price', 'price_change', 'price_change_percent')
    list_filter = ('commodity', 'timestamp')
    search_fields = ('commodity__name', 'commodity__symbol')
    readonly_fields = ('created_at',)
    
    def price_change(self, obj):
        """Display price change with color coding."""
        if obj.price_change > 0:
            return format_html(
                '<span style="color: green;">+{:.2f}</span>',
                obj.price_change
            )
        elif obj.price_change < 0:
            return format_html(
                '<span style="color: red;">{:.2f}</span>',
                obj.price_change
            )
        return format_html('{:.2f}', obj.price_change)
    price_change.short_description = 'Price Change'
    
    def price_change_percent(self, obj):
        """Display price change percentage with color coding."""
        if obj.price_change_percent > 0:
            return format_html(
                '<span style="color: green;">+{:.2f}%</span>',
                obj.price_change_percent
            )
        elif obj.price_change_percent < 0:
            return format_html(
                '<span style="color: red;">{:.2f}%</span>',
                obj.price_change_percent
            )
        return format_html('{:.2f}%', obj.price_change_percent)
    price_change_percent.short_description = 'Change %'


@admin.register(MarketUpdate)
class MarketUpdateAdmin(admin.ModelAdmin):
    """Admin configuration for MarketUpdate model."""
    
    list_display = (
        'id_short', 'data_source', 'commodity', 'status',
        'duration', 'records_processed', 'created_at'
    )
    list_filter = ('status', 'data_source', 'commodity')
    search_fields = ('commodity__name', 'data_source__name', 'task_id')
    readonly_fields = (
        'task_id', 'started_at', 'completed_at', 'duration',
        'records_processed', 'records_created', 'records_updated',
        'records_failed', 'error_message', 'created_at'
    )
    
    def id_short(self, obj):
        """Display shortened version of the UUID."""
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def duration(self, obj):
        """Display duration in a human-readable format."""
        if obj.duration:
            return str(obj.duration)
        return '-'
    duration.short_description = 'Duration' 