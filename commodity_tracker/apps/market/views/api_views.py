"""
API views for the market application.
"""
import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status as drf_status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny # Or IsAuthenticated, etc.

from apps.market.models import Commodity, CommodityCategory, PriceData, DataSource, MarketUpdate
from apps.market.serializers import (
    CommoditySerializer, CommodityDetailSerializer, CommodityCategorySerializer,
    PriceDataSerializer, DataSourceSerializer, MarketUpdateLogSerializer
)
from apps.market.tasks import update_single_commodity_prices_task, update_all_active_commodities_prices_task
from .base import BaseAPIView # Use our custom BaseAPIView for error handling

logger = logging.getLogger(__name__)


class CommodityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing Commodities.
    Provides `list` and `retrieve` actions by default.
    """
    queryset = Commodity.active.all().select_related('category', 'data_source').order_by('name')
    serializer_class = CommoditySerializer
    permission_classes = [AllowAny] # Adjust as needed
    lookup_field = 'id' # Use UUID for lookup, can also add lookup by symbol if needed

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CommodityDetailSerializer
        return CommoditySerializer

    @action(detail=False, methods=['get'], url_path='by-symbol/(?P<symbol>[^/.]+)')
    def by_symbol(self, request, symbol=None):
        """Retrieve a commodity by its symbol."""
        commodity = get_object_or_404(Commodity.active, symbol__iexact=symbol)
        serializer = CommodityDetailSerializer(commodity, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='trigger-update')
    def trigger_update_action(self, request, id=None): # 'id' matches lookup_field
        """
        Triggers an asynchronous price update for this specific commodity.
        Accessible via /api/market/v1/commodities/{id}/trigger-update/
        """
        commodity = self.get_object() # Gets commodity by ID
        logger.info(f"API trigger_update action called for commodity: {commodity.symbol}")

        task_kwargs = request.data.get('fetch_kwargs', {}) # Allow passing fetch_kwargs via request body
        task = update_single_commodity_prices_task.delay(commodity_id=str(commodity.id), **task_kwargs)
        
        return Response(
            {'message': f'Price update task for {commodity.symbol} has been queued.', 'task_id': task.id},
            status=drf_status.HTTP_202_ACCEPTED
        )

    @action(detail=False, methods=['get'])
    def needs_update(self, request):
        """Returns commodities that might need a price update (e.g., no recent data)."""
        hours = int(request.query_params.get('hours', 24))
        commodities_to_update = Commodity.objects.get_commodities_for_update(hours=hours)
        page = self.paginate_queryset(commodities_to_update)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(commodities_to_update, many=True)
        return Response(serializer.data)


class CommodityCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing Commodity Categories."""
    queryset = CommodityCategory.objects.all().prefetch_related('commodities').order_by('name')
    serializer_class = CommodityCategorySerializer
    permission_classes = [AllowAny]


class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing Data Sources."""
    queryset = DataSource.objects.all().order_by('name')
    serializer_class = DataSourceSerializer
    permission_classes = [AllowAny]


class PriceDataViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing Price Data."""
    queryset = PriceData.objects.all().select_related('commodity').order_by('-timestamp')
    serializer_class = PriceDataSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['commodity', 'commodity__symbol', 'timestamp'] # Enable filtering

    def get_queryset(self):
        qs = super().get_queryset()
        commodity_id = self.request.query_params.get('commodity_id')
        commodity_symbol = self.request.query_params.get('commodity_symbol')
        
        if commodity_id:
            qs = qs.filter(commodity_id=commodity_id)
        elif commodity_symbol:
            qs = qs.filter(commodity__symbol__iexact=commodity_symbol)
            
        # Date range filtering
        date_from_str = self.request.query_params.get('date_from')
        date_to_str = self.request.query_params.get('date_to')
        if date_from_str:
            date_from = timezone.datetime.strptime(date_from_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            qs = qs.filter(timestamp__gte=date_from)
        if date_to_str:
            date_to = (timezone.datetime.strptime(date_to_str, '%Y-%m-%d') + timedelta(days=1)).replace(tzinfo=timezone.utc)
            qs = qs.filter(timestamp__lt=date_to)
            
        return qs


class MarketUpdateLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for viewing Market Update Logs."""
    queryset = MarketUpdate.objects.all().select_related('data_source', 'commodity').order_by('-started_at', '-created_at')
    serializer_class = MarketUpdateLogSerializer
    permission_classes = [AllowAny] # Adjust if logs are sensitive
    filterset_fields = ['status', 'data_source', 'commodity', 'commodity__symbol']


# Standalone API Views (not part of ViewSets, using BaseAPIView for error handling)

class TriggerCommodityUpdateView(BaseAPIView):
    """
    Standalone API view to trigger an asynchronous price update for a specific commodity.
    Example URL: /api/market/v1/commodities/{commodity_id}/trigger-update/
    """
    permission_classes = [AllowAny] # Or IsAdminUser, etc.

    def post(self, request, commodity_id, *args, **kwargs): # commodity_id from URL
        commodity = self.get_commodity_or_404(commodity_id) # Uses helper from BaseAPIView
        logger.info(f"API TriggerCommodityUpdateView POST called for commodity: {commodity.symbol}")

        task_kwargs = request.data.get('fetch_kwargs', {}) # Allow passing fetch_kwargs
        task = update_single_commodity_prices_task.delay(commodity_id=str(commodity.id), **task_kwargs)

        return self.success_response(
            data={'task_id': task.id},
            message=f'Price update task for {commodity.symbol} has been queued.',
            status=drf_status.HTTP_202_ACCEPTED
        )


class TriggerAllCommoditiesUpdateView(BaseAPIView):
    """
    Standalone API view to trigger an asynchronous price update for ALL active commodities.
    Example URL: /api/market/v1/commodities/trigger-update-all/
    """
    permission_classes = [AllowAny] # Or IsAdminUser, etc.

    def post(self, request, *args, **kwargs):
        logger.info("API TriggerAllCommoditiesUpdateView POST called.")

        task_kwargs = request.data.get('fetch_kwargs', {}) # Allow passing fetch_kwargs
        task = update_all_active_commodities_prices_task.delay(**task_kwargs)

        return self.success_response(
            data={'task_id': task.id},
            message='Task to update all active commodities has been queued.',
            status=drf_status.HTTP_202_ACCEPTED
        )


class CommodityPriceHistoryView(generics.ListAPIView): # Using DRF's ListAPIView for convenience
    """
    API view to get price history for a specific commodity.
    Example URL: /api/market/v1/commodities/{commodity_id}/price-history/?days=60
    """
    serializer_class = PriceDataSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        commodity_id_or_symbol = self.kwargs.get('commodity_id') # From URL
        # Use the helper from BaseAPIView (though generics.ListAPIView doesn't inherit it directly)
        # For simplicity, re-implement or ensure it's available.
        try:
            from uuid import UUID
            commodity = get_object_or_404(Commodity.active, id=UUID(str(commodity_id_or_symbol)))
        except (ValueError, TypeError):
            commodity = get_object_or_404(Commodity.active, symbol__iexact=str(commodity_id_or_symbol))
        
        days_str = self.request.query_params.get('days', '30')
        try:
            days = int(days_str)
            if not (1 <= days <= 3650 * 2): # Limit days (e.g., up to 20 years)
                days = 30
        except ValueError:
            days = 30

        start_date = timezone.now() - timedelta(days=days)
        return PriceData.objects.filter(commodity=commodity, timestamp__gte=start_date).order_by('timestamp')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        commodity_id_or_symbol = self.kwargs.get('commodity_id')
        days_param = self.request.query_params.get('days', '30')

        if not queryset.exists():
            return Response(
                {'message': f'No price history found for commodity {commodity_id_or_symbol} in the last {days_param} days.'},
                status=drf_status.HTTP_404_NOT_FOUND
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data) 