from rest_framework import serializers

from transactions.models import BankAccount, Coupon, Order, OrderItem, PayoutRequest
from .models import Product, SellerProfile,Service

from django.contrib.auth.password_validation import validate_password


class ProductSerializer(serializers.ModelSerializer):
    seller = serializers.ReadOnlyField(source="seller.id")

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = (
            "id",
            "slug",
            "rating",
            "review_count",
            "stock_sold",
            "created_at",
            "updated_at",
        )



class ServiceSerializer(serializers.ModelSerializer):
    seller = serializers.ReadOnlyField(source="seller.id")

    class Meta:
        model = Service
        fields = "__all__"
        read_only_fields = (
            "id",
            "slug",
            "rating",
            "review_count",
            "created_at",
            "updated_at",
        )


class DashboardSerializer(serializers.Serializer):
    cards = serializers.DictField()
    chart = serializers.ListField()
    bestsellers = serializers.ListField()
    orders = serializers.ListField()




class OrderItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(source="product.name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "service",
            "product_name",
            "service_name",
            "quantity",
            "price",
        ]



class OrderListSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True, read_only=True)

    revenue = serializers.SerializerMethodField()
    net_profit = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "buyer_name",
            "buyer_email",
            "status",
            "total_amount",
            "revenue",
            "net_profit",
            "created_at",
            "items",
            "address",
            "city", 
            "state",   
            "country",
            "postal_code",
            "buyer_phone"

        ]

    def get_revenue(self, obj):
        return obj.total_amount

    def get_net_profit(self, obj):
        return float(obj.total_amount) * 0.85
    

class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["status"]  # only allow status

class CouponSerializer(serializers.ModelSerializer):

   
    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "discount_type",
            "discount_value",
            "usage_limit",
            "used_count",
            "expiry_date",
            "status",
            "created_at",
        ]

        read_only_fields = ["id", "used_count", "status", "created_at"]


class SellerProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = SellerProfile
        fields = "__all__"
        read_only_fields = ["user", "slug", "rating", "review_count"]




class BankAccountSerializer(serializers.ModelSerializer):

    class Meta:
        model = BankAccount
        fields = "__all__"
        read_only_fields = ["seller"]



class PayoutRequestSerializer(serializers.ModelSerializer):

    class Meta:
        model = PayoutRequest
        fields = "__all__"
        read_only_fields = ["seller", "status"]




class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "New passwords do not match."})
        
        # Check if old password is correct
        user = self.context['request'].user
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError({"old_password": "Wrong old password."})
            
        return attrs