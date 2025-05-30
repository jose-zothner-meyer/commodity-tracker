"""
Web views for the market application.
"""
from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from apps.market.models import Commodity, PriceData, DataSource, MarketUpdate
from .base import BaseTemplateView
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin

class CommodityListView(BaseTemplateView):
    model = Commodity
    template_name = 'market/web/commodity_list.html'
    context_object_name = 'commodities'
    paginate_by = 15
    page_title = "Commodities Overview"

    def get_queryset(self):
        return Commodity.active.all().select_related('category', 'data_source').order_by('name')


class CommodityDetailView(BaseTemplateView):
    model = Commodity
    template_name = 'market/web/commodity_detail.html'
    context_object_name = 'commodity'

    def get_queryset(self):
        return Commodity.objects.all().select_related('category', 'data_source')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        commodity = self.object
        context['page_title'] = f"{commodity.name} ({commodity.symbol})"

        days_history = int(self.request.GET.get('days', 30))
        if not (1 <= days_history <= 365 * 5): days_history = 30

        price_history = PriceData.objects.filter(
            commodity=commodity,
            timestamp__gte=timezone.now() - timedelta(days=days_history)
        ).order_by('timestamp')

        context['price_history'] = price_history
        context['price_history_days'] = days_history

        if price_history:
            context['chart_labels'] = [p.timestamp.strftime('%Y-%m-%d') for p in price_history]
            context['chart_data_close'] = [float(p.close_price) for p in price_history]
        return context


class DataSourceListView(BaseTemplateView):
    model = DataSource
    template_name = 'market/web/datasource_list.html'
    context_object_name = 'datasources'
    paginate_by = 20
    page_title = "Data Sources"

    def get_queryset(self):
        return DataSource.objects.all().order_by('name')


class DataSourceDetailView(BaseTemplateView):
    model = DataSource
    template_name = 'market/web/datasource_detail.html'
    context_object_name = 'datasource'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        datasource = self.object
        context['page_title'] = f"Data Source: {datasource.name}"
        context['commodities_using_source'] = Commodity.objects.filter(data_source=datasource, is_active=True).order_by('name')[:20]
        context['update_logs'] = MarketUpdate.objects.filter(data_source=datasource).order_by('-started_at')[:20]
        return context


class MarketUpdateLogListView(BaseTemplateView):
    model = MarketUpdate
    template_name = 'market/web/marketupdatelog_list.html'
    context_object_name = 'update_logs'
    paginate_by = 25
    page_title = "Market Update Logs"

    def get_queryset(self):
        return MarketUpdate.objects.all().select_related('data_source', 'commodity').order_by('-started_at', '-created_at')


class MarketUpdateLogDetailView(BaseTemplateView):
    model = MarketUpdate
    template_name = 'market/web/marketupdatelog_detail.html'
    context_object_name = 'update_log'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        update_log = self.object
        context['page_title'] = f"Update Log Details: {update_log.id_short()}"
        return context 