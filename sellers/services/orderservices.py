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
    

    ALLOWED_STATUSES = ["COMPLETED", "PROCESSING", "PAID", "CANCELLED", "SHIPPED", "OUT_FOR_DELIVERY"]

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
        
        # -- Trigger Notifications to Customer --
        from core.email_service import send_notification
        
        if new_status == "SHIPPED" and order.buyer:
            # Assuming tracking number is available or left blank for now
            tracking_number = "N/A"
            send_notification(
                user=order.buyer,
                title=f"Order #{order.id} Shipped",
                message=f"Your order #{order.id} has been shipped.",
                notification_type="ORDER",
                email_template="customers/order_shipped.html",
                email_subject="Your Order is on the Way!",
                email_context={
                    "name": order.buyer_name,
                    "order_id": order.id,
                    "tracking_number": tracking_number,
                    "tracking_url": f"https://jefedo.com/orders/{order.id}/track"
                }
            )
        elif new_status == "OUT_FOR_DELIVERY" and order.buyer:
            send_notification(
                user=order.buyer,
                title=f"Order #{order.id} Out for Delivery",
                message=f"Your order #{order.id} is out for delivery today.",
                notification_type="ORDER",
                email_template="customers/out_for_delivery.html",
                email_subject="Out for Delivery",
                email_context={
                    "name": order.buyer_name,
                    "order_id": order.id
                }
            )
        elif new_status == "COMPLETED" and order.buyer:
            send_notification(
                user=order.buyer,
                title=f"Order #{order.id} Delivered",
                message=f"Your order #{order.id} has been delivered successfully.",
                notification_type="ORDER",
                email_template="customers/order_delivered.html",
                email_subject="Order Delivered",
                email_context={
                    "name": order.buyer_name,
                    "order_id": order.id,
                    "review_url": f"https://jefedo.com/orders/{order.id}/review"
                }
            )

        return order