"""
URL configuration for the market app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'data-sources', views.DataSourceViewSet)
router.register(r'categories', views.CommodityCategoryViewSet)
router.register(r'commodities', views.CommodityViewSet)
router.register(r'prices', views.PriceDataViewSet)
router.register(r'updates', views.MarketUpdateViewSet)

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
] 