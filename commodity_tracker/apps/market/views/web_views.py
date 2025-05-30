"""
Web views for the market application.
"""
from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from apps.market.models import Commodity, PriceData, DataSource, MarketUpdate
from .base import BaseTemplateView, AuthenticatedBaseTemplateView
from django.utils import timezone
from datetime import timedelta
from django.db.models import Prefetch
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

class CommodityListView(AuthenticatedBaseTemplateView):
    """
    View for listing all active commodities.
    
    Attributes:
        model: Commodity model
        template_name: Path to the template
        context_object_name: Name of the context variable
        paginate_by: Number of items per page
        page_title: Title of the page
    """
    model = Commodity
    template_name = 'market/web/commodity_list.html'
    context_object_name = 'commodities'
    paginate_by = 15
    page_title = "Commodities Overview"

    def get_queryset(self):
        """Get queryset with optimized database queries."""
        return Commodity.active.all().select_related(
            'category', 
            'data_source'
        ).prefetch_related(
            Prefetch(
                'pricedata_set',
                queryset=PriceData.objects.order_by('-timestamp')[:1],
                to_attr='_latest_price'
            )
        ).order_by('name')


class CommodityDetailView(AuthenticatedBaseTemplateView):
    """
    View for displaying detailed information about a specific commodity.
    
    Attributes:
        model: Commodity model
        template_name: Path to the template
        context_object_name: Name of the context variable
    """
    model = Commodity
    template_name = 'market/web/commodity_detail.html'
    context_object_name = 'commodity'

    def get_queryset(self):
        """Get queryset with optimized database queries."""
        return Commodity.objects.select_related(
            'category', 
            'data_source'
        ).prefetch_related(
            'pricedata_set'
        )

    def get_context_data(self, **kwargs):
        """Add price history and chart data to the context."""
        context = super().get_context_data(**kwargs)
        commodity = self.object
        context['page_title'] = f"{commodity.name} ({commodity.symbol})"

        days_history = int(self.request.GET.get('days', 30))
        if not (1 <= days_history <= 365 * 5): 
            days_history = 30

        price_history = PriceData.objects.filter(
            commodity=commodity,
            timestamp__gte=timezone.now() - timedelta(days=days_history)
        ).order_by('timestamp')

        context['price_history'] = price_history
        context['price_history_days'] = days_history

        if price_history:
            chart_data = {
                'labels': [p.timestamp.strftime('%Y-%m-%d') for p in price_history],
                'datasets': [{
                    'label': 'Close Price',
                    'data': [float(p.close_price) for p in price_history],
                    'borderColor': 'rgb(75, 192, 192)',
                    'tension': 0.1,
                    'fill': False
                }]
            }
            context['chart_data'] = json.dumps(chart_data, cls=DecimalEncoder)
        return context


class DataSourceListView(AuthenticatedBaseTemplateView):
    """
    View for listing all data sources.
    
    Attributes:
        model: DataSource model
        template_name: Path to the template
        context_object_name: Name of the context variable
        paginate_by: Number of items per page
        page_title: Title of the page
    """
    model = DataSource
    template_name = 'market/web/datasource_list.html'
    context_object_name = 'datasources'
    paginate_by = 20
    page_title = "Data Sources"

    def get_queryset(self):
        """Get queryset with optimized database queries."""
        return DataSource.objects.prefetch_related(
            'commodity_set'
        ).order_by('name')


class DataSourceDetailView(AuthenticatedBaseTemplateView):
    """
    View for displaying detailed information about a specific data source.
    
    Attributes:
        model: DataSource model
        template_name: Path to the template
        context_object_name: Name of the context variable
    """
    model = DataSource
    template_name = 'market/web/datasource_detail.html'
    context_object_name = 'datasource'

    def get_context_data(self, **kwargs):
        """Add related commodities and update logs to the context."""
        context = super().get_context_data(**kwargs)
        datasource = self.object
        context['page_title'] = f"Data Source: {datasource.name}"
        context['commodities'] = Commodity.objects.filter(
            data_source=datasource, 
            is_active=True
        ).select_related('category').order_by('name')[:20]
        context['update_logs'] = MarketUpdate.objects.filter(
            data_source=datasource
        ).select_related('commodity').order_by('-started_at')[:20]
        return context


class MarketUpdateLogListView(AuthenticatedBaseTemplateView):
    """
    View for listing all market update logs.
    
    Attributes:
        model: MarketUpdate model
        template_name: Path to the template
        context_object_name: Name of the context variable
        paginate_by: Number of items per page
        page_title: Title of the page
    """
    model = MarketUpdate
    template_name = 'market/web/marketupdatelog_list.html'
    context_object_name = 'update_logs'
    paginate_by = 25
    page_title = "Market Update Logs"

    def get_queryset(self):
        """Get queryset with optimized database queries."""
        return MarketUpdate.objects.select_related(
            'data_source', 
            'commodity'
        ).order_by('-started_at', '-created_at')


class MarketUpdateLogDetailView(AuthenticatedBaseTemplateView):
    """
    View for displaying detailed information about a specific market update log.
    
    Attributes:
        model: MarketUpdate model
        template_name: Path to the template
        context_object_name: Name of the context variable
    """
    model = MarketUpdate
    template_name = 'market/web/marketupdatelog_detail.html'
    context_object_name = 'update_log'

    def get_context_data(self, **kwargs):
        """Add page title to the context."""
        context = super().get_context_data(**kwargs)
        update_log = self.object
        context['page_title'] = f"Update Log Details: {update_log.id_short()}"
        return context 