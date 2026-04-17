from django.contrib import admin
from .models import Order, OrderItem,PayoutRequest

# Register your models here.
admin.site.register(PayoutRequest)
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