"""
payments/checkout_service.py

All business logic for:
  - Validating items (stock, availability)
  - Applying coupons
  - Creating Order + OrderItems
  - Creating a pending Transaction
  - Initialising payment with Paystack

NOTE ON ATOMICITY:
  The DB writes (Order, OrderItems, Transaction) are wrapped in their own
  atomic block. The Paystack API call happens AFTER the DB commit so that
  a Paystack network error does not roll back a valid order.
  If Paystack fails, the order stays in PENDING status and can be retried.
"""
import logging
from decimal import Decimal

from django.db import transaction as db_transaction

from  transactions.models import Order, OrderItem
from sellers.models import Product, Service
from  transactions.models import Transaction, Coupon
from . import paystack as ps

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────
#  INTERNAL HELPERS
# ─────────────────────────────────────────────────

def _resolve_product_items(raw_items: list) -> list:
    resolved = []
    for item in raw_items:
        try:
            product = Product.objects.get(pk=item["item_id"], status="PUBLISHED")
        except Product.DoesNotExist:
            raise ValueError(f"Product #{item['item_id']} not found or not available.")

        qty = item["quantity"]
        if product.stock_qty < qty:
            raise ValueError(
                f"Insufficient stock for '{product.name}'. "
                f"Available: {product.stock_qty}, requested: {qty}."
            )

        resolved.append(
            {"product": product, "service": None, "quantity": qty, "unit_price": product.price}
        )
    return resolved


def _resolve_service_items(raw_items: list) -> list:
    resolved = []
    for item in raw_items:
        try:
            service = Service.objects.get(pk=item["item_id"], status="PUBLISHED")
        except Service.DoesNotExist:
            raise ValueError(f"Service #{item['item_id']} not found or not available.")

        resolved.append(
            {"product": None, "service": service, "quantity": 1, "unit_price": service.price}
        )
    return resolved


def _apply_coupon(coupon_code: str, seller_id: int, subtotal: Decimal):
    if not coupon_code:
        return None, Decimal("0")

    try:
        coupon = Coupon.objects.get(code=coupon_code, seller_id=seller_id)
    except Coupon.DoesNotExist:
        raise ValueError("Invalid coupon code.")

    coupon_status = coupon.status()
    if coupon_status == "EXPIRED":
        raise ValueError("This coupon has expired.")
    if coupon_status == "USED_UP":
        raise ValueError("This coupon has reached its usage limit.")

    if coupon.discount_type == "PERCENTAGE":
        discount = (coupon.discount_value / Decimal("100")) * subtotal
    else:
        discount = min(coupon.discount_value, subtotal)

    return coupon, discount.quantize(Decimal("0.01"))


def _compute_total(resolved_items: list) -> Decimal:
    total = Decimal("0")
    for item in resolved_items:
        total += item["unit_price"] * item["quantity"]
    return total


# ─────────────────────────────────────────────────
#  DB-ONLY WRITES (inside atomic block)
# ─────────────────────────────────────────────────

@db_transaction.atomic
def _create_product_order(validated_data, user, resolved, coupon, discount, total) -> tuple:
    """Create Order + OrderItems + Transaction in one atomic DB transaction."""
    order = Order.objects.create(
        buyer=user if user and user.is_authenticated else None,
        buyer_name=validated_data["buyer_name"],
        buyer_email=validated_data["buyer_email"],
        buyer_phone=validated_data.get("buyer_phone", ""),
        order_type="PRODUCT",
        total_amount=total,
        discount_amount=discount,
        coupon=coupon,
        address=validated_data["address"],
        city=validated_data["city"],
        state=validated_data["state"],
        country=validated_data.get("country", "Nigeria"),
        postal_code=validated_data.get("postal_code", ""),
    )

    for item in resolved:
        OrderItem.objects.create(
            order=order,
            product=item["product"],
            service=None,
            quantity=item["quantity"],
            price=item["unit_price"],
        )
        p = item["product"]
        p.stock_qty -= item["quantity"]
        p.stock_sold += item["quantity"]
        p.save(update_fields=["stock_qty", "stock_sold"])

    if coupon:
        coupon.used_count += 1
        coupon.save(update_fields=["used_count"])

    reference = ps.generate_reference()
    txn = Transaction.objects.create(
        order=order,
        reference=reference,
        amount=total,
        currency="NGN",
    )

    return order, txn, reference


@db_transaction.atomic
def _create_service_order(validated_data, user, resolved, coupon, discount, total) -> tuple:
    """Create Order + OrderItems + Transaction for a service booking."""
    order = Order.objects.create(
        buyer=user if user and user.is_authenticated else None,
        buyer_name=validated_data["buyer_name"],
        buyer_email=validated_data["buyer_email"],
        buyer_phone=validated_data.get("buyer_phone", ""),
        order_type="SERVICE",
        total_amount=total,
        discount_amount=discount,
        coupon=coupon,
        booking_date=validated_data["booking_date"],
        booking_time=validated_data["booking_time"],
        booking_notes=validated_data.get("booking_notes", ""),
    )

    for item in resolved:
        OrderItem.objects.create(
            order=order,
            product=None,
            service=item["service"],
            quantity=item["quantity"],
            price=item["unit_price"],
        )

    if coupon:
        coupon.used_count += 1
        coupon.save(update_fields=["used_count"])

    reference = ps.generate_reference()
    txn = Transaction.objects.create(
        order=order,
        reference=reference,
        amount=total,
        currency="NGN",
    )

    return order, txn, reference


# ─────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────

def initiate_product_checkout(validated_data: dict, user=None) -> dict:
    """
    Full product checkout flow.
    DB writes happen first (atomic), then Paystack is called.
    If Paystack fails, the order stays PENDING — it can be retried.
    """
    raw_items = validated_data["items"]
    coupon_code = validated_data.get("coupon_code", "")

    # 1. Validate
    resolved = _resolve_product_items(raw_items)
    seller_id = resolved[0]["product"].seller_id
    subtotal = _compute_total(resolved)
    coupon, discount = _apply_coupon(coupon_code, seller_id, subtotal)
    total = subtotal - discount

    # 2. Write to DB (atomic — if this fails nothing is saved)
    order, txn, reference = _create_product_order(
        validated_data, user, resolved, coupon, discount, total
    )

    # 3. Call Paystack (outside atomic — network failure won't roll back DB)
    metadata = {
        "order_id": order.id,
        "order_type": "PRODUCT",
        "buyer_name": order.buyer_name,
    }
    ps_data = ps.initialize_transaction(
        email=order.buyer_email,
        amount_naira=float(total),
        reference=reference,
        metadata=metadata,
    )

    return {
        "order": order,
        "transaction": txn,
        "payment_url": ps_data["authorization_url"],
        "reference": reference,
        "access_code": ps_data["access_code"],
    }


def initiate_service_checkout(validated_data: dict, user=None) -> dict:
    """
    Full service booking checkout flow.
    DB writes happen first (atomic), then Paystack is called.
    """
    raw_items = validated_data["items"]
    coupon_code = validated_data.get("coupon_code", "")

    # 1. Validate
    resolved = _resolve_service_items(raw_items)
    seller_id = resolved[0]["service"].seller_id
    subtotal = _compute_total(resolved)
    coupon, discount = _apply_coupon(coupon_code, seller_id, subtotal)
    total = subtotal - discount

    # 2. Write to DB (atomic)
    order, txn, reference = _create_service_order(
        validated_data, user, resolved, coupon, discount, total
    )

    # 3. Call Paystack
    metadata = {
        "order_id": order.id,
        "order_type": "SERVICE",
        "buyer_name": order.buyer_name,
        "booking_date": str(validated_data["booking_date"]),
        "booking_time": str(validated_data["booking_time"]),
    }
    ps_data = ps.initialize_transaction(
        email=order.buyer_email,
        amount_naira=float(total),
        reference=reference,
        metadata=metadata,
    )

    return {
        "order": order,
        "transaction": txn,
        "payment_url": ps_data["authorization_url"],
        "reference": reference,
        "access_code": ps_data["access_code"],
    }


@db_transaction.atomic
def _update_payment_records(reference: str) -> dict:
    try:
        txn = Transaction.objects.select_related("order").get(reference=reference)
    except Transaction.DoesNotExist:
        raise ValueError(f"Transaction with reference '{reference}' not found.")
 
    # Already processed — nothing to do.
    if txn.status == "SUCCESS":
        return {"already_done": True, "order": txn.order, "transaction": txn}
 
    ps_data        = ps.verify_transaction(reference)
    gateway_status = ps_data.get("status")
    gateway_resp   = ps_data.get("gateway_response", "")
    amount_naira   = Decimal(str(ps_data.get("amount", 0))) / Decimal("100")
    paid_at        = ps_data.get("paid_at")
    paystack_id    = str(ps_data.get("id", ""))
 
    order = txn.order
 
    # ── SUCCESS path ─────────────────────────────────────────────────────────
    if gateway_status == "success":
        txn.status           = "SUCCESS"
        txn.amount_paid      = amount_naira
        txn.paystack_id      = paystack_id
        txn.gateway_response = gateway_resp
        txn.paid_at          = paid_at
        txn.save()
 
        order.status = "PAID"
        order.save(update_fields=["status"])
 
        # Collect everything needed for emails while we're still inside the
        # transaction and the related objects are warm in memory.
        items_data          = []
        vendor_notifications = []
 
        for item in order.items.select_related(
            "product__seller__user", "service__seller__user"
        ).all():
            if item.product:
                item_name   = item.product.name
                seller_user = getattr(item.product.seller, "user", None)
                seller_name = getattr(item.product.seller, "store_name", "")
            elif item.service:
                item_name   = item.service.name
                seller_user = getattr(item.service.seller, "user", None)
                seller_name = getattr(item.service.seller, "store_name", "")
            else:
                item_name   = "Unknown item"
                seller_user = None
                seller_name = ""
 
            items_data.append({
                "name":     item_name,
                "quantity": item.quantity,
                "price":    str(item.price),
            })
 
            if seller_user:
                vendor_notifications.append({
                    "user":        seller_user,
                    "item_name":   item_name,
                    "seller_name": seller_name,
                })
 
        return {
            "already_done":         False,
            "success":              True,
            "order":                order,
            "transaction":          txn,
            "items_data":           items_data,
            "vendor_notifications": vendor_notifications,
        }
 
    # ── FAILURE path ─────────────────────────────────────────────────────────
    txn.status           = "FAILED" if gateway_status == "failed" else "ABANDONED"
    txn.gateway_response = gateway_resp
    txn.save()
 
    order.status = "CANCELLED"
    order.save(update_fields=["status"])
 
    # Restore stock — DB operation, fine inside the transaction.
    if order.order_type == "PRODUCT":
        for item in order.items.select_related("product").all():
            if item.product:
                item.product.stock_qty  += item.quantity
                item.product.stock_sold  = max(0, item.product.stock_sold - item.quantity)
                item.product.save(update_fields=["stock_qty", "stock_sold"])
 
    return {
        "already_done":   False,
        "success":        False,
        "order":          order,
        "transaction":    txn,
        "gateway_response": gateway_resp,
    }
 
 
# ---------------------------------------------------------------------------
# Public — calls _update_payment_records then fires emails AFTER commit.
# ---------------------------------------------------------------------------
 
def handle_payment_verification(reference: str) -> dict:
    """
    Verify a Paystack payment and update Order + Transaction accordingly.
    Idempotent — safe to call multiple times.
 
    The DB update is fully atomic. Emails are sent only after the transaction
    commits, so an email failure can never roll back the order status.
    Each email is individually guarded — one failure won't block the others.
    """
    from core.email_service import send_jefedo_email, send_notification
 
    result = _update_payment_records(reference)
 
    # Already processed on a previous call — nothing left to do.
    if result["already_done"]:
        return {
            "success":     True,
            "order":       result["order"],
            "transaction": result["transaction"],
        }
 
    order = result["order"]
    txn   = result["transaction"]
 
    # ── SUCCESS emails ────────────────────────────────────────────────────────
    if result["success"]:
 
        # 1. Payment confirmation to buyer
        try:
            send_jefedo_email(
                to_email      = order.buyer_email,
                subject       = "Payment Successful – Jefedo",
                template_name = "customers/payment_successful.html",
                context       = {
                    "name":     order.buyer_name,
                    "amount":   str(txn.amount_paid),
                    "order_id": order.id,
                },
            )
        except Exception:
            logger.exception("Failed to send payment-success email for order %s", order.id)
 
        # 2. New-order notification to each vendor
        for vendor in result.get("vendor_notifications", []):
            try:
                send_notification(
                    user              = vendor["user"],
                    title             = f"New Order #{order.id}",
                    message           = f"You received an order for {vendor['item_name']}.",
                    notification_type = "ORDER",
                    email_template    = "vendors/new_order_received.html",
                    email_subject     = "New Order Received! – Jefedo",
                    email_context     = {
                        "vendor_name":   vendor["seller_name"],
                        "order_id":      order.id,
                        "dashboard_url": "https://jefedo.com/dashboard/orders",
                    },
                )
            except Exception:
                logger.exception(
                    "Failed to send vendor notification for order %s to user %s",
                    order.id, vendor["user"].id,
                )
 
        # 3. Order confirmation to buyer
        try:
            send_jefedo_email(
                to_email      = order.buyer_email,
                subject       = f"Order Confirmation #{order.id} – Jefedo",
                template_name = "customers/order_confirmation.html",
                context       = {
                    "name":         order.buyer_name,
                    "order_id":     order.id,
                    "items":        result.get("items_data", []),
                    "total_amount": str(order.total_amount),
                    "order_url":    f"https://jefedo.com/orders/{order.id}",
                },
            )
        except Exception:
            logger.exception("Failed to send order-confirmation email for order %s", order.id)
 
    # ── FAILURE email ─────────────────────────────────────────────────────────
    else:
        try:
            send_jefedo_email(
                to_email      = order.buyer_email,
                subject       = "Payment Failed – Jefedo",
                template_name = "customers/failed_payment.html",
                context       = {
                    "name":          order.buyer_name,
                    "order_id":      order.id,
                    "amount":        str(txn.amount),
                    "error_message": result["gateway_response"] or "Payment was abandoned or failed.",
                    "checkout_url":  f"https://jefedo.com/checkout/{order.id}",
                },
            )
        except Exception:
            logger.exception("Failed to send payment-failed email for order %s", order.id)
 
    return {
        "success":     result["success"],
        "order":       order,
        "transaction": txn,
    }
 