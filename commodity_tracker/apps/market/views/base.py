"""
Base view classes for the market application.
"""
import logging
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.views import APIView
from rest_framework import status as drf_status
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from apps.core.mixins import CacheResponseMixin, JSONResponseMixin
from apps.core.exceptions import CommodityTrackerException
from apps.market.models import Commodity

logger = logging.getLogger(__name__)

class AuthenticatedBaseTemplateView(LoginRequiredMixin, BaseTemplateView):
    """
    Base template view that requires authentication.
    """
    login_url = reverse_lazy('admin:login')
    redirect_field_name = 'next'

class BaseTemplateView(CacheResponseMixin, TemplateView):
    """
    Base template view with caching.
    Subclasses should define `template_name`.
    """
    cache_timeout = 300  # 5 minutes, can be overridden

    def get_cache_timeout(self):
        """Get the cache timeout for this view."""
        return getattr(self, 'cache_timeout', 300)

    def get_cache_key(self):
        """Get the cache key for this view."""
        return f"{self.__class__.__name__}:{self.request.path}"

    def get_context_data(self, **kwargs):
        """Add common context data."""
        context = super().get_context_data(**kwargs)
        context['page_title'] = getattr(self, 'page_title', 
            self.model._meta.verbose_name_plural if hasattr(self, 'model') and self.model else "Page")
        return context

    def handle_exception(self, request, exception):
        """Handle exceptions in template views."""
        logger.error(f"Error in {self.__class__.__name__}: {exception}", exc_info=True)
        context = self.get_context_data()
        context['error_message'] = str(exception)
        return self.render_to_response(context, status=500)

    def dispatch(self, request, *args, **kwargs):
        """Log request information."""
        logger.info(f"Processing {request.method} request to {request.path}")
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            return self.handle_exception(request, e)

class BaseAPIView(JSONResponseMixin, APIView):
    """
    Base API view with standardized error handling and utility methods.
    Inherits JSONResponseMixin for success_response and error_response methods.
    """
    def handle_exception(self, exc):
        """
        Handles exceptions raised in API views.
        Returns a standardized JSON error response.
        """
        if isinstance(exc, Http404):
            logger.warning(f"Resource not found (404): {exc}")
            return self.error_response(str(exc), status=drf_status.HTTP_404_NOT_FOUND)

        if isinstance(exc, CommodityTrackerException):
            logger.warning(f"CommodityTrackerException handled in API: {exc}")
            custom_status = getattr(exc, 'status_code', drf_status.HTTP_400_BAD_REQUEST)
            return self.error_response(str(exc), status=custom_status)

        logger.error(f"Unhandled exception in API view: {exc}", exc_info=True)
        return self.error_response(
            "An unexpected server error occurred.",
            status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    def get_commodity_or_404(self, commodity_id_or_symbol, queryset=None):
        """
        Retrieves an active commodity by its UUID or symbol.
        Raises Http404 if not found.
        """
        if queryset is None:
            queryset = Commodity.active.all()

        try:
            from uuid import UUID
            uuid_obj = UUID(str(commodity_id_or_symbol), version=4)
            return get_object_or_404(queryset, id=uuid_obj)
        except (ValueError, TypeError):
            return get_object_or_404(queryset, symbol__iexact=str(commodity_id_or_symbol))
        except Commodity.DoesNotExist:
            raise Http404(f"Commodity with identifier '{commodity_id_or_symbol}' not found.") 