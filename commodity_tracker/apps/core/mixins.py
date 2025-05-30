"""
Reusable mixins for the application.
"""
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
# from django.core.cache import cache # Not directly used in these mixins

class CacheResponseMixin:
    """
    Mixin to add caching functionality to class-based views.
    Caches the response of the dispatch method.
    """
    cache_timeout = 300  # 5 minutes default, can be overridden in subclass

    @method_decorator(cache_page(cache_timeout))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class JSONResponseMixin:
    """Mixin to provide standardized JSON response functionality for views."""

    def json_response(self, data, status=200, safe=False, **kwargs):
        """Return a JSON response."""
        return JsonResponse(data, status=status, safe=safe, **kwargs)

    def success_response(self, data, message="Success", status=200, **kwargs):
        """Return a success JSON response with a standard structure."""
        response_data = {
            'status': 'success',
            'message': message,
            'data': data
        }
        return self.json_response(response_data, status=status, **kwargs)

    def error_response(self, message, error_code=None, status=400, **kwargs):
        """Return an error JSON response with a standard structure."""
        response_data = {'status': 'error', 'message': message}
        if error_code:
            response_data['error_code'] = error_code
        return self.json_response(response_data, status=status, **kwargs)


class TimestampMixin:
    """Mixin to add timestamp utility functionality (not directly for models)."""

    def get_current_timestamp(self):
        """Get current timezone-aware timestamp."""
        from django.utils import timezone
        return timezone.now() 