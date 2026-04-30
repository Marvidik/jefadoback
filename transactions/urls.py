from django.urls import path
from .views import *

urlpatterns = [
    path("checkout/product/", ProductCheckoutView.as_view(), name="product-checkout"),
    path("checkout/service/", ServiceCheckoutView.as_view(), name="service-checkout"),
    path("checkout/verify/<reference>/",VerifyPaymentView.as_view(),name="paystack-verify"),
]