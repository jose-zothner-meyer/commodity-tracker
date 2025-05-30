"""
Serializers for the market app models.
"""
from rest_framework import serializers
from .models import (
    DataSource,
    CommodityCategory,
    Commodity,
    PriceData,
    MarketUpdate
)


class DataSourceSerializer(serializers.ModelSerializer):
    """Serializer for the DataSource model."""
    
    class Meta:
        model = DataSource
        fields = [
            'id', 'name', 'base_url', 'api_key_required',
            'rate_limit_per_minute', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class CommodityCategorySerializer(serializers.ModelSerializer):
    """Serializer for the CommodityCategory model."""
    
    active_commodities_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CommodityCategory
        fields = [
            'id', 'name', 'description', 'active_commodities_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_active_commodities_count(self, obj):
        """Returns the count of active commodities in this category."""
        return obj.active_commodities_count()


class CommoditySerializer(serializers.ModelSerializer):
    """Serializer for the Commodity model."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)
    latest_price = serializers.SerializerMethodField()
    price_change = serializers.SerializerMethodField()
    
    class Meta:
        model = Commodity
        fields = [
            'id', 'name', 'symbol', 'category', 'category_name',
            'exchange', 'unit', 'currency', 'data_source',
            'data_source_name', 'is_active', 'latest_price',
            'price_change', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_latest_price(self, obj):
        """Returns the latest price data for the commodity."""
        latest_price = obj.get_latest_price()
        if latest_price:
            return {
                'price': latest_price.close_price,
                'timestamp': latest_price.timestamp,
                'change': latest_price.price_change,
                'change_percent': latest_price.price_change_percent
            }
        return None
    
    def get_price_change(self, obj):
        """Returns the price change over the last 24 hours."""
        latest_price = obj.get_latest_price()
        if latest_price:
            return {
                'change': latest_price.price_change,
                'change_percent': latest_price.price_change_percent
            }
        return None


class PriceDataSerializer(serializers.ModelSerializer):
    """Serializer for the PriceData model."""
    
    commodity_name = serializers.CharField(source='commodity.name', read_only=True)
    price_change = serializers.FloatField(read_only=True)
    price_change_percent = serializers.FloatField(read_only=True)
    
    class Meta:
        model = PriceData
        fields = [
            'id', 'commodity', 'commodity_name', 'timestamp',
            'open_price', 'high_price', 'low_price', 'close_price',
            'volume', 'price_change', 'price_change_percent',
            'source_data', 'created_at'
        ]
        read_only_fields = ['created_at']


class MarketUpdateSerializer(serializers.ModelSerializer):
    """Serializer for the MarketUpdate model."""
    
    commodity_name = serializers.CharField(source='commodity.name', read_only=True)
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)
    duration = serializers.DurationField(read_only=True)
    
    class Meta:
        model = MarketUpdate
        fields = [
            'id', 'data_source', 'data_source_name', 'commodity',
            'commodity_name', 'status', 'task_id', 'started_at',
            'completed_at', 'duration', 'records_processed',
            'records_created', 'records_updated', 'records_failed',
            'error_message', 'created_at'
        ]
        read_only_fields = [
            'started_at', 'completed_at', 'duration',
            'records_processed', 'records_created', 'records_updated',
            'records_failed', 'error_message', 'created_at'
        ]

class MarketUpdateLogSerializer(serializers.ModelSerializer):
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)
    commodity_symbol = serializers.CharField(source='commodity.symbol', read_only=True, allow_null=True)
    duration = serializers.DurationField(read_only=True, allow_null=True)

    class Meta:
        model = MarketUpdate
        fields = [
            'id', 'data_source', 'data_source_name', 'commodity', 'commodity_symbol',
            'status', 'task_id', 'records_fetched', 'records_created', 'records_updated',
            'error_message', 'started_at', 'completed_at', 'duration',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'data_source_name', 'commodity_symbol', 'duration', 'created_at', 'updated_at')
        extra_kwargs = { # For creating/updating if needed, though often handled by services
            'data_source': {'write_only': True},
            'commodity': {'write_only': True, 'required': False, 'allow_null': True},
        } 