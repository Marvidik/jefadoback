from django.urls import path
from .views import (
    CategoryListView,
    ProductDetailView,
    ReviewCreateView,
    ServiceDetailView,
    ServiceListView,
    AlmostSoldOutProductsView,
    FeaturedProductsView,
    ProductListView,
    ShopDetailView,
    ShopListingsView,
)

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),

    path('services/', ServiceListView.as_view(), name='service-list'),
    path('products/almost-sold-out/', AlmostSoldOutProductsView.as_view(), name='almost-sold-out'),
    path('products/featured/', FeaturedProductsView.as_view(), name='featured-products'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product-detail'),
    path('services/<slug:slug>/', ServiceDetailView.as_view(), name='service-detail'),

    path('reviews/', ReviewCreateView.as_view(), name='review-create'),

    path('shops/<slug:slug>/', ShopDetailView.as_view(), name='shop-detail'),
    path('shops/<slug:slug>/listings/', ShopListingsView.as_view(), name='shop-listings'),
]