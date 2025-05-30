# This file would typically override settings from base.py for development.
# For simplicity in this example, most settings are controlled by .env and DEBUG flag in base.py.
# You can create this file and commodity_tracker/settings/production.py
# and use an environment variable (e.g., DJANGO_SETTINGS_MODULE) to switch between them.
# Example:
# from .base import *
# DEBUG = True
# ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*'] # More permissive for dev
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# # Add Django Debug Toolbar settings if used
# # INSTALLED_APPS += ['debug_toolbar']
# # MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
# # INTERNAL_IPS = ['127.0.0.1'] 

from .base import *
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*'] # More permissive for dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Add Django Debug Toolbar settings if used
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
# INTERNAL_IPS = ['127.0.0.1'] 