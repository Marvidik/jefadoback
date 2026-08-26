from decimal import Decimal
from rest_framework import serializers
from .models import Wallet, WalletTransaction


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ["id", "currency", "balance", "status", "created_at"]
        read_only_fields = fields


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            "id", "reference", "type", "direction", "amount",
            "balance_before", "balance_after", "status",
            "order", "description", "created_at",
        ]
        read_only_fields = fields


class WalletFundInitiateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("100"))


class AdminWalletAdjustmentSerializer(serializers.Serializer):
    direction = serializers.ChoiceField(choices=["CREDIT", "DEBIT"])
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    reason = serializers.CharField(max_length=255)