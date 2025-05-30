"""
Serializers for commodity-related models.
"""
from rest_framework import serializers
from ..models import (
    Commodity,
    PriceData,
    MarketUpdate,
    DataSource,
    CommodityCategory,
)

class DataSourceSerializer(serializers.ModelSerializer):
    """Serializer for the DataSource model."""
    class Meta:
        model = DataSource
        fields = ['id', 'name', 'description', 'is_active']

class CommodityCategorySerializer(serializers.ModelSerializer):
    """Serializer for the CommodityCategory model."""
    class Meta:
        model = CommodityCategory
        fields = ['id', 'name', 'description']

class PriceDataSerializer(serializers.ModelSerializer):
    """Serializer for the PriceData model."""
    class Meta:
        model = PriceData
        fields = [
            'id', 'timestamp', 'open_price', 'high_price', 'low_price',
            'close_price', 'volume', 'adjusted_close', 'dividend_amount',
            'split_coefficient'
        ]

class MarketUpdateSerializer(serializers.ModelSerializer):
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)
    commodity_symbol = serializers.CharField(source='commodity.symbol', read_only=True)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = MarketUpdate
        fields = [
            'id', 'data_source_name', 'commodity_symbol', 'status',
            'started_at', 'completed_at', 'duration', 'records_fetched',
            'records_created', 'records_updated', 'error_message'
        ]
        read_only_fields = ['started_at', 'completed_at', 'duration']

    def get_duration(self, obj):
        return obj.duration

class CommoditySerializer(serializers.ModelSerializer):
    """Serializer for the Commodity model."""
    category = CommodityCategorySerializer(read_only=True)
    data_source = DataSourceSerializer(read_only=True)
    latest_price = PriceDataSerializer(read_only=True)

    class Meta:
        model = Commodity
        fields = [
            'id', 'name', 'symbol', 'description', 'category',
            'data_source', 'is_active', 'last_updated', 'latest_price'
        ]

class CommodityListSerializer(CommoditySerializer):
    class Meta(CommoditySerializer.Meta):
        fields = [
            'id', 'name', 'symbol', 'category', 'data_source',
            'is_active', 'last_updated', 'latest_price'
        ]

class CommodityDetailSerializer(CommoditySerializer):
    price_history = serializers.SerializerMethodField()

    class Meta(CommoditySerializer.Meta):
        fields = CommoditySerializer.Meta.fields + ['price_history']

    def get_price_history(self, obj):
        # Get the last 30 days of price data
        price_data = obj.price_data.all().order_by('-timestamp')[:30]
        return PriceDataSerializer(price_data, many=True).data 