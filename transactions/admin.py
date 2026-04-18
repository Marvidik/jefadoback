from django.contrib import admin
from .models import Order, OrderItem,PayoutRequest,Transaction, Coupon, BankAccount, PayoutRequest


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # readonly_fields = ("price",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "buyer_name",
        "buyer_email",
        "order_type",
        "status",
        "total_amount",
        "created_at",
    )

    list_filter = (
        "status",
        "order_type",
        "created_at",
    )

    search_fields = (
        "buyer_name",
        "buyer_email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "product",
        "service",
        "quantity",
        "price",
    )

    search_fields = (
        "order__buyer_name",
        "order__buyer_email",
    )

    list_filter = (
        "order__status",
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "order", "amount", "amount_paid", "status", "paid_at", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("reference", "paystack_id", "order__buyer_email")
    readonly_fields = ("reference", "paystack_id", "gateway_response", "paid_at", "created_at", "updated_at")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "seller", "discount_type", "discount_value", "used_count", "usage_limit", "expiry_date")
    search_fields = ("code", "seller__store_name")
    list_filter = ("discount_type",)


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("seller", "bank_name", "account_name", "account_number", "is_default")
    list_filter = ("is_default",)
    search_fields = ("seller__store_name", "account_number")


@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ("seller", "bank_account", "amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("seller__store_name",)