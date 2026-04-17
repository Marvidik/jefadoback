from django.db.models import Sum, Count, F, FloatField, ExpressionWrapper
from django.utils.timezone import now
from datetime import timedelta
from collections import defaultdict

from transactions.models import Order, OrderItem
from ..models import Product


class DashboardService:

    @staticmethod
    def get_date_range(days):
        end = now()
        start = end - timedelta(days=days)
        return start, end

    # -------------------------
    # CARDS
    # -------------------------

    @staticmethod
    def get_summary_cards(seller):

        orders = Order.objects.filter(items__product__seller=seller).distinct()

        total_revenue = orders.aggregate(
            total=Sum("total_amount")
        )["total"] or 0

        total_orders = orders.count()

        # fake visitors placeholder (replace with real Visitor model later)
        total_visitors = 15500

        conversion_rate = (
            (total_orders / total_visitors) * 100
            if total_visitors else 0
        )

        # previous period (last 30 days vs previous 30 days)
        _, end = DashboardService.get_date_range(30)
        prev_start = end - timedelta(days=30)

        prev_orders = Order.objects.filter(
            created_at__range=(prev_start, end),
            items__product__seller=seller
        ).distinct()

        prev_revenue = prev_orders.aggregate(total=Sum("total_amount"))["total"] or 0

        def pct_change(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return ((current - previous) / previous) * 100

        return {
            "total_revenue": {
                "value": total_revenue,
                "change_pct": pct_change(total_revenue, prev_revenue),
            },
            "total_orders": {
                "value": total_orders,
                "change_pct": pct_change(total_orders, prev_orders.count()),
            },
            "total_visitors": {
                "value": total_visitors,
                "change_pct": 49,
            },
            "conversion_rate": {
                "value": round(conversion_rate, 2),
                "change_pct": 1.8,
            },
        }

    # -------------------------
    # MONTHLY CHART
    # -------------------------

    @staticmethod
    def get_monthly_earnings(seller):

        orders = Order.objects.filter(
            items__product__seller=seller,
            status="PAID"
        ).annotate(
            month=F("created_at__month")
        )

        data = defaultdict(float)

        for order in orders:
            month = order.created_at.strftime("%b")
            data[month] += float(order.total_amount)

        return [
            {"month": k, "earnings": v}
            for k, v in data.items()
        ]

    # -------------------------
    # BEST SELLING PRODUCTS
    # -------------------------

    @staticmethod
    def get_best_selling_products(seller):

        products = Product.objects.filter(
            seller=seller,
            order_items__isnull=False
        ).annotate(
            units_sold=Count("order_items"),
            revenue=Sum("order_items__price"),
            net_profit=ExpressionWrapper(
                Sum("order_items__price") * 0.85,
                output_field=FloatField()
            )
        ).order_by("-units_sold")[:10]

        return products

    # -------------------------
    # ORDERS TABLE
    # -------------------------

    @staticmethod
    def get_recent_orders(seller):

        return Order.objects.filter(
            items__product__seller=seller
        ).annotate(
            revenue=Sum("total_amount"),
            net_profit=ExpressionWrapper(
                Sum("total_amount") * 0.85,
                output_field=FloatField()
            )
        ).distinct().order_by("-created_at")[:20]