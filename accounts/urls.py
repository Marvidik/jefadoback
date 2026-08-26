# urls.py
from django.urls import path
from .views import (
    NotificationListView,NotificationMarkAllReadView, NotificationMarkReadView, UnreadNotificationCountView, UserOrderListView, UserProfileView, AddressListCreateView, AddressDetailView, SetDefaultAddressView,
    WishlistListView, WishlistAddView, ChangePasswordView, WishlistRemoveView,VerifyLoginOTPView,TwoFactorToggleView
)

urlpatterns = [
    path('two-factor/toggle/', TwoFactorToggleView.as_view(), name='two-factor-toggle'),

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


    #notification
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/unread-count/', UnreadNotificationCountView.as_view(), name='notification-unread-count'),
    path('notifications/mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
    path('notifications/<int:pk>/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
]