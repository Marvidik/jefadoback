from django.urls import path
from .views import *

urlpatterns = [
    path("products/", ProductListCreateView.as_view(), name="product-list-create"),
    path("products/<int:pk>/", ProductRetrieveUpdateDeleteView.as_view(), name="product-detail"),
    path("services/", ServiceListCreateView.as_view(), name="service-list-create"),
    path("services/<int:pk>/", ServiceRetrieveUpdateDeleteView.as_view(), name="service-detail"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("orders/analytics/", OrderAnalyticsView.as_view()),
    path("orders/", OrderListPageView.as_view()),
    path("list/services/",ServiceOrderListPageView.as_view(),name="service-order-list"),
    path("coupons/", CouponListCreateView.as_view()),
    path("coupons/<int:pk>/", CouponUpdateView.as_view()),
    path("coupons/<int:pk>/delete/", CouponDeleteView.as_view()),
    path("profile/", SellerProfileView.as_view(), name="seller-profile"),

    path("bank-accounts/", BankAccountListCreateView.as_view(), name="bank-account-list-create"),
    path("bank-accounts/<int:pk>/delete/", BankAccountDeleteView.as_view(), name="bank-account-delete"),
    path("payout-requests/", PayoutRequestListCreateView.as_view(), name="payout-request-list-create"), 
    path("list/payout-requests/", PayoutRequestListCreateView.as_view(), name="payout-request-list"),

    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]