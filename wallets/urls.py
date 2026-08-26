from django.urls import path
from .views import (
    WalletDetailView, WalletTransactionListView,
    WalletFundInitiateView, WalletFundVerifyView,
)

urlpatterns = [
    path('', WalletDetailView.as_view(), name='wallet-detail'),
    path('transactions/', WalletTransactionListView.as_view(), name='wallet-transactions'),
    path('fund/initiate/', WalletFundInitiateView.as_view(), name='wallet-fund-initiate'),
    path('fund/verify/<str:reference>/', WalletFundVerifyView.as_view(), name='wallet-fund-verify'),
]