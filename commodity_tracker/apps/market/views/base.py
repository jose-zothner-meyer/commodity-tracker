"""
Base view classes for the market application.
"""
import logging
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.views import APIView
from rest_framework import status as drf_status # Alias to avoid conflict with model status
from apps.core.mixins import CacheResponseMixin, JSONResponseMixin
from apps.core.exceptions import CommodityTrackerException
from apps.market.models import Commodity # For get_commodity_or_404

logger = logging.getLogger(__name__)


class BaseTemplateView(CacheResponseMixin, TemplateView):
    """
    Base template view with caching.
    Subclasses should define `template_name`.
    """
    cache_timeout = 300  # 5 minutes, can be overridden

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = getattr(self, 'page_title', self.model._meta.verbose_name_plural if hasattr(self, 'model') and self.model else "Page")
        return context


class BaseAPIView(JSONResponseMixin, APIView):
    """
    Base API view with standardized error handling and utility methods.
    Inherits JSONResponseMixin for success_response and error_response methods.
    """
    # permission_classes = [] # Define default permissions if needed

    def handle_exception(self, exc):
        """
        Handles exceptions raised in API views.
        Returns a standardized JSON error response.
        """
        if isinstance(exc, Http404): # Handle Django's Http404 specifically
            logger.warning(f"Resource not found (404): {exc}")
            return self.error_response(str(exc), status=drf_status.HTTP_404_NOT_FOUND)

        if isinstance(exc, CommodityTrackerException):
            logger.warning(f"CommodityTrackerException handled in API: {exc}")
            # Determine status code based on exception type if needed, default to 400
            custom_status = getattr(exc, 'status_code', drf_status.HTTP_400_BAD_REQUEST)
            return self.error_response(str(exc), status=custom_status)

        # For other unhandled exceptions, log them as errors and return a generic 500 response
        logger.error(f"Unhandled exception in API view: {exc}", exc_info=True)
        return self.error_response(
            "An unexpected server error occurred.",
            status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    def get_commodity_or_404(self, commodity_id_or_symbol, queryset=None):
        """
        Retrieves an active commodity by its UUID or symbol.
        Raises Http404 if not found.
        `queryset` can be provided to use a specific pre-filtered queryset.
        """
        if queryset is None:
            queryset = Commodity.active.all() # Default to active commodities

        try:
            # Check if it's a UUID
            from uuid import UUID
            uuid_obj = UUID(str(commodity_id_or_symbol), version=4)
            return get_object_or_404(queryset, id=uuid_obj)
        except (ValueError, TypeError):
            # Not a valid UUID, try symbol (case-insensitive)
            return get_object_or_404(queryset, symbol__iexact=str(commodity_id_or_symbol))
        except Commodity.DoesNotExist: # Should be caught by get_object_or_404
            raise Http404(f"Commodity with identifier '{commodity_id_or_symbol}' not found.") 