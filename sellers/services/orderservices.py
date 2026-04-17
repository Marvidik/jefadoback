from django.db.models import Sum, Count
from django.utils.timezone import now
from datetime import timedelta
from collections import defaultdict

from transactions.models import Order


class OrderAnalyticsService:

    @staticmethod
    def get_base_queryset(seller):
        return Order.objects.filter(
            items__product__seller=seller
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