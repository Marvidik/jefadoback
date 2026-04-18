# urls.py
from django.urls import path
from .views import (
    UserOrderListView, UserProfileView, AddressListCreateView, AddressDetailView, SetDefaultAddressView,
    WishlistListView, WishlistAddView, ChangePasswordView, WishlistRemoveView
)

urlpatterns = [
    # Profile
    path('profile/', UserProfileView.as_view(), name='user-profile'),

    # Addresses
    path('addresses/', AddressListCreateView.as_view(), name='address-list'),
    path('addresses/<int:pk>/', AddressDetailView.as_view(), name='address-detail'),
    path('addresses/<int:pk>/set-default/', SetDefaultAddressView.as_view(), name='set-default-address'),

    # Wishlist
    path('wishlist/', WishlistListView.as_view(), name='wishlist-list'),
    path('wishlist/add/', WishlistAddView.as_view(), name='wishlist-add'),
    path('wishlist/remove/<int:product_id>/', WishlistRemoveView.as_view(), name='wishlist-remove'),

    # Password
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),

    path('orders/', UserOrderListView.as_view(), name='user-orders'),
]