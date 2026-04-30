from django.db.models import Sum, Count
from django.utils.timezone import now
from datetime import timedelta
from collections import defaultdict
from django.db import transaction
from transactions.models import Order
from django.db.models import Q

class OrderAnalyticsService:

    @staticmethod
    def get_base_queryset(seller):
        return Order.objects.filter(
            items__product__seller=seller,status__in=["COMPLETED","PROCESSING","PAID"]
        ).distinct()

    # -------------------------
    # CARDS
    # -------------------------
    @staticmethod
    def get_cards(seller):

        orders = OrderAnalyticsService.get_base_queryset(seller)

        revenue = orders.aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        order_count = orders.count()

        # fake placeholder (replace later with VisitorLog if needed)
        visitors = 15500

        conversion = (order_count / visitors * 100) if visitors else 0

        # previous 30 days
        end = now()
        start = end - timedelta(days=30)

        prev_orders = OrderAnalyticsService.get_base_queryset(seller).filter(
            created_at__range=(start, end)
        )

        prev_revenue = prev_orders.aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        def pct(curr, prev):
            if prev == 0:
                return 100 if curr > 0 else 0
            return ((curr - prev) / prev) * 100

        return {
            "revenue": {
                "value": revenue,
                "change_pct": pct(revenue, prev_revenue),
            },
            "orders": {
                "value": order_count,
                "change_pct": pct(order_count, prev_orders.count()),
            },
            "visitors": {
                "value": visitors,
                "change_pct": 49,
            },
            "conversion": {
                "value": round(conversion, 2),
                "change_pct": 1.8,
            },
        }

    # -------------------------
    # BAR CHART (ORDERS BY MONTH + QUANTITY)
    # -------------------------
    @staticmethod
    def get_chart(seller):

        orders = OrderAnalyticsService.get_base_queryset(seller)

        data = defaultdict(int)

        for order in orders:
            month = order.created_at.strftime("%b")
            data[month] += order.items.count()

        return [
            {"month": k, "orders": v}
            for k, v in data.items()
        ]
    

    ALLOWED_STATUSES = ["COMPLETED", "PROCESSING", "PAID", "CANCELLED"]

    @staticmethod
    @transaction.atomic
    def update_order_status(order_id, new_status, seller):
        try:
            order = Order.objects.select_for_update().get(
                Q(items__product__seller=seller) |
                Q(items__service__seller=seller),   
                id=order_id
            )
        except Order.DoesNotExist:
            raise ValueError("Order not found")

        if new_status not in OrderAnalyticsService.ALLOWED_STATUSES:
            raise ValueError("Invalid status")

        # Optional: enforce transition rules (important)
        if order.status == "COMPLETED":
            raise ValueError("Completed orders cannot be modified")

        order.status = new_status
        order.save(update_fields=["status"])

        return order