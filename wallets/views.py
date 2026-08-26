import uuid
from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model

from .models import WalletTransaction
from .serializers import (
    WalletSerializer, WalletTransactionSerializer,
    WalletFundInitiateSerializer, AdminWalletAdjustmentSerializer,
)
from .services import WalletService, InsufficientBalanceError, WalletFrozenError
from transactions.services import paystack as ps  # reuse your existing wrapper

User = get_user_model()


class WalletDetailView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return WalletService.get_or_create_wallet(self.request.user)


class WalletTransactionListView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["type", "direction", "status"]

    def get_queryset(self):
        wallet = WalletService.get_or_create_wallet(self.request.user)
        return wallet.transactions.all()




class WalletFundInitiateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = WalletFundInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        wallet = WalletService.get_or_create_wallet(request.user)
        reference = f"WLT-{ps.generate_reference()}"

        WalletService.initiate_funding(wallet, amount, reference)

        try:
            ps_data = ps.initialize_transaction(
                email=request.user.email,
                amount_naira=float(amount),
                reference=reference,
                metadata={"purpose": "WALLET_FUNDING", "user_id": request.user.id},
            )
        except Exception as e:
            WalletService.fail_funding(reference, reason=str(e))
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            "reference": reference,
            "payment_url": ps_data["authorization_url"],
            "access_code": ps_data["access_code"],
            "amount": str(amount),
        }, status=status.HTTP_201_CREATED)


class WalletFundVerifyView(APIView):
    """Polled from the frontend after Paystack redirects back — same
    idempotent pattern as your existing VerifyPaymentView."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, reference):
        try:
            txn = WalletTransaction.objects.get(reference=reference, wallet__user=request.user)
        except WalletTransaction.DoesNotExist:
            return Response({"detail": "Transaction not found."}, status=404)

        if txn.status == "SUCCESS":
            return Response({"success": True, "transaction": WalletTransactionSerializer(txn).data})

        try:
            ps_data = ps.verify_transaction(reference)
        except Exception as e:
            return Response({"detail": str(e)}, status=502)

        if ps_data.get("status") == "success":
            txn = WalletService.complete_funding(reference)
            return Response({"success": True, "transaction": WalletTransactionSerializer(txn).data})

        WalletService.fail_funding(reference, reason=ps_data.get("gateway_response", ""))
        return Response({"success": False, "detail": "Payment was not successful."})


