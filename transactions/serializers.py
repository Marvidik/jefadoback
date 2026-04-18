from rest_framework import serializers
from .models import Order, OrderItem
from sellers.models import Product, Service
from .models import Coupon, Transaction


# ─────────────────────────────────────────
#  ORDER ITEM serializers (read)
# ─────────────────────────────────────────

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "service",
            "service_name",
            "quantity",
            "price",
            "subtotal",
        ]

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    def get_service_name(self, obj):
        return obj.service.name if obj.service else None

    def get_subtotal(self, obj):
        return obj.get_subtotal()


# ─────────────────────────────────────────
#  CHECKOUT INPUT serializers
# ─────────────────────────────────────────

class CheckoutItemInputSerializer(serializers.Serializer):
    """One line item in the checkout payload."""
    item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class ProductCheckoutSerializer(serializers.Serializer):
    """Full payload for a PRODUCT checkout."""

    buyer_name = serializers.CharField(max_length=255)
    buyer_email = serializers.EmailField()
    buyer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    # Shipping
    address = serializers.CharField()
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=100)
    country = serializers.CharField(max_length=100, default="Nigeria")
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)

    items = CheckoutItemInputSerializer(many=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one item is required.")
        return items


class ServiceCheckoutSerializer(serializers.Serializer):
    """Full payload for a SERVICE checkout."""

    buyer_name = serializers.CharField(max_length=255)
    buyer_email = serializers.EmailField()
    buyer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    # Booking
    booking_date = serializers.DateField()
    booking_time = serializers.TimeField()
    booking_notes = serializers.CharField(required=False, allow_blank=True)

    items = CheckoutItemInputSerializer(many=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one item is required.")
        return items

    def validate_booking_date(self, value):
        from datetime import date
        if value < date.today():
            raise serializers.ValidationError("Booking date cannot be in the past.")
        return value


# ─────────────────────────────────────────
#  ORDER read serializer (response)
# ─────────────────────────────────────────

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    transaction_reference = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "buyer_name",
            "buyer_email",
            "buyer_phone",
            "order_type",
            "total_amount",
            "discount_amount",
            # product fields
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            # service fields
            "booking_date",
            "booking_time",
            "booking_notes",
            # meta
            "status",
            "coupon",
            "transaction_reference",
            "payment_status",
            "created_at",
            "items",
        ]

    def get_transaction_reference(self, obj):
        try:
            return obj.transaction.reference
        except Exception:
            return None

    def get_payment_status(self, obj):
        try:
            return obj.transaction.status
        except Exception:
            return None


# ─────────────────────────────────────────
#  TRANSACTION serializer
# ─────────────────────────────────────────

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "order",
            "reference",
            "paystack_id",
            "amount",
            "amount_paid",
            "currency",
            "status",
            "gateway_response",
            "paid_at",
            "created_at",
        ]




class CheckoutResponseSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(help_text="ID of the created order")
    reference = serializers.CharField(help_text="Unique payment reference e.g. TXN-ABCDEF123456")
    payment_url = serializers.URLField(help_text="Paystack hosted checkout URL — redirect the user here")
    access_code = serializers.CharField(help_text="Paystack access code (for inline/popup integration)")
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Total charged in NGN")
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, help_text="Amount discounted by coupon")
 
 
class ServiceCheckoutResponseSerializer(CheckoutResponseSerializer):
    booking_date = serializers.DateField(help_text="Confirmed booking date")
    booking_time = serializers.TimeField(help_text="Confirmed booking time")
 
 
class VerifyPaymentResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(help_text="True if payment was successful")
    message = serializers.CharField(help_text="Human-readable status message")
    order = serializers.DictField(help_text="Full order object")
    transaction = serializers.DictField(help_text="Full transaction object")
 
 
class WebhookResponseSerializer(serializers.Serializer):
    status = serializers.CharField(help_text="Always 'ok' — Paystack requires 200 to stop retrying")
 