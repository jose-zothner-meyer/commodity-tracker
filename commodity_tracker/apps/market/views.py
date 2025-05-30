"""
Views for the market app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Q
from .models import (
    DataSource,
    CommodityCategory,
    Commodity,
    PriceData,
    MarketUpdate
)
from .serializers import (
    DataSourceSerializer,
    CommodityCategorySerializer,
    CommoditySerializer,
    PriceDataSerializer,
    MarketUpdateSerializer
)
from .services.update_service import MarketUpdateService


class DataSourceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing data sources."""
    
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test the connection to the data source."""
        data_source = self.get_object()
        try:
            # Implement connection testing logic here
            return Response({'status': 'success', 'message': 'Connection successful'})
        except Exception as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CommodityCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing commodity categories."""
    
    queryset = CommodityCategory.objects.all()
    serializer_class = CommodityCategorySerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def commodities(self, request, pk=None):
        """Get all commodities in this category."""
        category = self.get_object()
        commodities = category.commodity_set.all()
        serializer = CommoditySerializer(commodities, many=True)
        return Response(serializer.data)


class CommodityViewSet(viewsets.ModelViewSet):
    """ViewSet for managing commodities."""
    
    queryset = Commodity.objects.all()
    serializer_class = CommoditySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Custom queryset filtering."""
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__name__icontains=category)
        
        # Filter by data source
        data_source = self.request.query_params.get('data_source', None)
        if data_source:
            queryset = queryset.filter(data_source__name__icontains=data_source)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def price_history(self, request, pk=None):
        """Get price history for a commodity."""
        commodity = self.get_object()
        days = int(request.query_params.get('days', 30))
        
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        prices = commodity.prices.filter(timestamp__gte=cutoff_date)
        
        serializer = PriceDataSerializer(prices, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_price(self, request, pk=None):
        """Manually trigger a price update for a commodity."""
        commodity = self.get_object()
        update_service = MarketUpdateService()
        
        try:
            update = update_service.update_commodity_price(commodity)
            serializer = MarketUpdateSerializer(update)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'status': 'error', 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PriceDataViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing price data."""
    
    queryset = PriceData.objects.all()
    serializer_class = PriceDataSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Custom queryset filtering."""
        queryset = super().get_queryset()
        
        # Filter by commodity
        commodity = self.request.query_params.get('commodity', None)
        if commodity:
            queryset = queryset.filter(commodity__name__icontains=commodity)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset


class MarketUpdateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing market updates."""
    
    queryset = MarketUpdate.objects.all()
    serializer_class = MarketUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Custom queryset filtering."""
        queryset = super().get_queryset()
        
        # Filter by status
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by commodity
        commodity = self.request.query_params.get('commodity', None)
        if commodity:
            queryset = queryset.filter(commodity__name__icontains=commodity)
        
        # Filter by data source
        data_source = self.request.query_params.get('data_source', None)
        if data_source:
            queryset = queryset.filter(data_source__name__icontains=data_source)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get statistics about market updates."""
        queryset = self.get_queryset()
        
        # Get counts by status
        status_counts = queryset.values('status').annotate(count=Count('id'))
        
        # Get average duration
        avg_duration = queryset.exclude(
            Q(started_at__isnull=True) | Q(completed_at__isnull=True)
        ).aggregate(
            avg_duration=models.Avg('duration')
        )
        
        # Get total records processed
        total_records = queryset.aggregate(
            total_processed=models.Sum('records_processed'),
            total_created=models.Sum('records_created'),
            total_updated=models.Sum('records_updated'),
            total_failed=models.Sum('records_failed')
        )
        
        return Response({
            'status_counts': status_counts,
            'average_duration': avg_duration,
            'total_records': total_records
        }) 