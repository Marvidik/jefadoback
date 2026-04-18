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
def handle_payment_verification(reference: str) -> dict:
    """
    Verify a Paystack payment and update Order + Transaction accordingly.
    Idempotent — safe to call multiple times.
    """
    try:
        txn = Transaction.objects.select_related("order").get(reference=reference)
    except Transaction.DoesNotExist:
        raise ValueError(f"Transaction with reference '{reference}' not found.")

    if txn.status == "SUCCESS":
        return {"success": True, "order": txn.order, "transaction": txn}

    ps_data = ps.verify_transaction(reference)

    gateway_status = ps_data.get("status")
    amount_paid_kobo = ps_data.get("amount", 0)
    amount_paid_naira = Decimal(str(amount_paid_kobo)) / Decimal("100")
    paid_at = ps_data.get("paid_at")
    paystack_id = str(ps_data.get("id", ""))
    gateway_response = ps_data.get("gateway_response", "")

    if gateway_status == "success":
        txn.status = "SUCCESS"
        txn.amount_paid = amount_paid_naira
        txn.paystack_id = paystack_id
        txn.gateway_response = gateway_response
        txn.paid_at = paid_at
        txn.save()

        order = txn.order
        order.status = "PAID"
        order.save(update_fields=["status"])

        return {"success": True, "order": order, "transaction": txn}

    else:
        txn.status = "FAILED" if gateway_status == "failed" else "ABANDONED"
        txn.gateway_response = gateway_response
        txn.save()

        order = txn.order
        order.status = "CANCELLED"
        order.save(update_fields=["status"])

        # Restore product stock on failure
        if order.order_type == "PRODUCT":
            for item in order.items.select_related("product").all():
                if item.product:
                    item.product.stock_qty += item.quantity
                    item.product.stock_sold = max(0, item.product.stock_sold - item.quantity)
                    item.product.save(update_fields=["stock_qty", "stock_sold"])

        return {"success": False, "order": order, "transaction": txn}