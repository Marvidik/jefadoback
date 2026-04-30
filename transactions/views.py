"""
payments/views.py
"""
import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
    inline_serializer,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers as drf_serializers

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Order
from .serializers import (
    ProductCheckoutSerializer,
    ServiceCheckoutSerializer,
    OrderSerializer,
    TransactionSerializer,
    CheckoutResponseSerializer,
    ServiceCheckoutResponseSerializer,
    VerifyPaymentResponseSerializer,
    WebhookResponseSerializer,
)
from .services import checkoutservice as  checkout_service

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────
#  PRODUCT CHECKOUT
# ─────────────────────────────────────────────────

class ProductCheckoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Checkout"],
        summary="Initiate product order checkout",
        description=(
            "Creates a product order and initialises a Paystack payment session. "
            "Returns a `payment_url` — redirect the user to this URL to complete payment. "
            "Works for both authenticated users and guests. "
            "Stock is held immediately; it is restored if payment fails or is abandoned."
        ),
        request=ProductCheckoutSerializer,
        responses={
            201: OpenApiResponse(
                response=CheckoutResponseSerializer,
                description="Order created. Redirect user to `payment_url`.",
            ),
            400: OpenApiResponse(description="Validation error or bad coupon / out-of-stock."),
            502: OpenApiResponse(description="Paystack gateway error."),
        },
        examples=[
            OpenApiExample(
                name="With coupon — two items",
                summary="Checkout with a coupon code and two product lines",
                value={
                    "buyer_name": "John Doe",
                    "buyer_email": "john@example.com",
                    "buyer_phone": "08012345678",
                    "address": "12 Marina Street",
                    "city": "Lagos",
                    "state": "Lagos",
                    "country": "Nigeria",
                    "postal_code": "100001",
                    "coupon_code": "SAVE10",
                    "items": [
                        {"item_id": 3, "quantity": 2},
                        {"item_id": 7, "quantity": 1},
                    ],
                },
                request_only=True,
            ),
            OpenApiExample(
                name="Guest checkout — no coupon",
                summary="Minimal guest checkout without a coupon",
                value={
                    "buyer_name": "Jane Smith",
                    "buyer_email": "jane@example.com",
                    "buyer_phone": "07055550000",
                    "address": "5 Admiralty Way",
                    "city": "Lekki",
                    "state": "Lagos",
                    "country": "Nigeria",
                    "items": [{"item_id": 1, "quantity": 1}],
                },
                request_only=True,
            ),
            OpenApiExample(
                name="201 — Order created",
                value={
                    "order_id": 12,
                    "reference": "TXN-ABCDEF12345678",
                    "payment_url": "https://checkout.paystack.com/xxxxxxxx",
                    "access_code": "xxxxxxxx",
                    "total_amount": "4500.00",
                    "discount_amount": "500.00",
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def post(self, request):
        serializer = ProductCheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = checkout_service.initiate_product_checkout(
                validated_data=serializer.validated_data,
                user=request.user,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Product checkout failed")
            # In DEBUG mode, surface the real error so you can diagnose it
            error_detail = str(e) if settings.DEBUG else "Payment gateway error. Please try again later."
            return Response({"detail": error_detail}, status=status.HTTP_502_BAD_GATEWAY)

        order = result["order"]
        print(result)
        return Response(
            {
                "order_id": order.id,
                "reference": result["reference"],
                "payment_url": result["payment_url"],
                "access_code": result["access_code"],
                "total_amount": str(order.total_amount),
                "discount_amount": str(order.discount_amount),
            },
            status=status.HTTP_201_CREATED,
        )


# ─────────────────────────────────────────────────
#  SERVICE CHECKOUT
# ─────────────────────────────────────────────────

class ServiceCheckoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Checkout"],
        summary="Initiate service booking checkout",
        description=(
            "Books a service with a chosen date and time, then initialises a Paystack payment session. "
            "Returns a `payment_url` — redirect the user here to complete payment. "
            "`booking_date` must not be in the past. "
            "Works for both authenticated users and guests."
        ),
        request=ServiceCheckoutSerializer,
        responses={
            201: OpenApiResponse(
                response=ServiceCheckoutResponseSerializer,
                description="Booking created. Redirect user to `payment_url`.",
            ),
            400: OpenApiResponse(
                description="Validation error — e.g. past booking date, invalid service ID, bad coupon."
            ),
            502: OpenApiResponse(description="Paystack gateway error."),
        },
        examples=[
            OpenApiExample(
                name="Service booking with coupon",
                summary="Book a service, pick date/time, apply coupon",
                value={
                    "buyer_name": "Jane Doe",
                    "buyer_email": "jane@example.com",
                    "buyer_phone": "08087654321",
                    "booking_date": "2026-05-10",
                    "booking_time": "14:30:00",
                    "booking_notes": "Please bring your own tools.",
                    "coupon_code": "FIRST20",
                    "items": [{"item_id": 5, "quantity": 1}],
                },
                request_only=True,
            ),
            OpenApiExample(
                name="Minimal service booking",
                summary="No coupon or notes — just the essentials",
                value={
                    "buyer_name": "Emeka Obi",
                    "buyer_email": "emeka@example.com",
                    "booking_date": "2026-06-01",
                    "booking_time": "09:00:00",
                    "items": [{"item_id": 8, "quantity": 1}],
                },
                request_only=True,
            ),
            OpenApiExample(
                name="201 — Booking created",
                value={
                    "order_id": 13,
                    "reference": "TXN-XYZ789ABCDEF01",
                    "payment_url": "https://checkout.paystack.com/yyyyyyyy",
                    "access_code": "yyyyyyyy",
                    "total_amount": "15000.00",
                    "discount_amount": "3000.00",
                    "booking_date": "2026-05-10",
                    "booking_time": "14:30:00",
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def post(self, request):
        serializer = ServiceCheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = checkout_service.initiate_service_checkout(
                validated_data=serializer.validated_data,
                user=request.user,
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Service checkout failed")
            error_detail = str(e) if settings.DEBUG else "Payment gateway error. Please try again later."
            return Response({"detail": error_detail}, status=status.HTTP_502_BAD_GATEWAY)

        order = result["order"]
        return Response(
            {
                "order_id": order.id,
                "reference": result["reference"],
                "payment_url": result["payment_url"],
                "access_code": result["access_code"],
                "total_amount": str(order.total_amount),
                "discount_amount": str(order.discount_amount),
                "booking_date": str(order.booking_date),
                "booking_time": str(order.booking_time),
            },
            status=status.HTTP_201_CREATED,
        )


# ─────────────────────────────────────────────────
#  PAYMENT VERIFICATION
# ─────────────────────────────────────────────────

class VerifyPaymentView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Checkout"],
        summary="Verify payment by reference",
        description=(
            "Verifies a Paystack transaction using the payment `reference`. "
            "Call this after Paystack redirects back to your site, or poll it from the frontend. "
            "**Idempotent** — safe to call multiple times for the same reference. "
            "\n\n"
            "On success → order status becomes `PAID`, transaction becomes `SUCCESS`. "
            "\n\n"
            "On failure/abandonment → order becomes `CANCELLED`, product stock is restored."
        ),
        parameters=[
            OpenApiParameter(
                name="reference",
                location=OpenApiParameter.PATH,
                description="The payment reference returned during checkout (e.g. `TXN-ABCDEF12345678`)",
                required=True,
                type=OpenApiTypes.STR,
            )
        ],
        responses={
            200: OpenApiResponse(
                response=VerifyPaymentResponseSerializer,
                description="Verification completed. Check `success` field for payment outcome.",
            ),
            404: OpenApiResponse(description="Transaction reference not found."),
            502: OpenApiResponse(description="Could not reach Paystack to verify."),
        },
        examples=[
            OpenApiExample(
                name="200 — Payment successful",
                value={
                    "success": True,
                    "message": "Payment successful.",
                    "order": {
                        "id": 12,
                        "buyer_name": "John Doe",
                        "buyer_email": "john@example.com",
                        "order_type": "PRODUCT",
                        "total_amount": "4500.00",
                        "status": "PAID",
                    },
                    "transaction": {
                        "reference": "TXN-ABCDEF12345678",
                        "amount": "4500.00",
                        "amount_paid": "4500.00",
                        "status": "SUCCESS",
                        "paid_at": "2026-04-18T12:00:00Z",
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                name="200 — Payment failed / abandoned",
                value={
                    "success": False,
                    "message": "Payment was not successful.",
                    "order": {"id": 12, "status": "CANCELLED"},
                    "transaction": {
                        "reference": "TXN-ABCDEF12345678",
                        "status": "ABANDONED",
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request, reference):
        try:
            result = checkout_service.handle_payment_verification(reference)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Payment verification failed")
            error_detail = str(e) if settings.DEBUG else "Verification failed. Please contact support."
            return Response({"detail": error_detail}, status=status.HTTP_502_BAD_GATEWAY)

        order_data = OrderSerializer(result["order"]).data
        txn_data = TransactionSerializer(result["transaction"]).data

        return Response(
            {
                "success": result["success"],
                "message": (
                    "Payment successful." if result["success"] else "Payment was not successful."
                ),
                "order": order_data,
                "transaction": txn_data,
            },
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────────
#  PAYSTACK WEBHOOK
# ─────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class PaystackWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Webhooks"],
        summary="Paystack webhook receiver",
        description=(
            "Receives server-to-server event notifications from Paystack. "
            "Register this URL in your Paystack dashboard under **Settings → Webhooks**. "
            "\n\n"
            "**Security:** Every request is verified using HMAC-SHA512 with your `PAYSTACK_SECRET_KEY`. "
            "Requests with invalid or missing signatures are rejected with 400. "
            "\n\n"
            "**Handled events:**\n"
            "- `charge.success` → marks transaction `SUCCESS`, order → `PAID`\n"
            "\n\n"
            "Always returns HTTP 200 so Paystack stops retrying."
        ),
        request=inline_serializer(
            name="PaystackWebhookPayload",
            fields={
                "event": drf_serializers.CharField(
                    help_text="Paystack event type e.g. 'charge.success'"
                ),
                "data": inline_serializer(
                    name="PaystackWebhookData",
                    fields={
                        "reference": drf_serializers.CharField(
                            help_text="Payment reference matching your transaction"
                        ),
                        "status": drf_serializers.CharField(
                            help_text="'success', 'failed', or 'abandoned'"
                        ),
                        "amount": drf_serializers.IntegerField(
                            help_text="Amount in kobo (÷100 = Naira)"
                        ),
                        "paid_at": drf_serializers.DateTimeField(
                            help_text="ISO8601 timestamp of payment"
                        ),
                    },
                ),
            },
        ),
        responses={
            200: OpenApiResponse(
                response=WebhookResponseSerializer,
                description="Always returned so Paystack stops retrying.",
            ),
            400: OpenApiResponse(description="Invalid HMAC signature or malformed JSON body."),
        },
        examples=[
            OpenApiExample(
                name="charge.success — Paystack sends this",
                value={
                    "event": "charge.success",
                    "data": {
                        "id": 302961,
                        "reference": "TXN-ABCDEF12345678",
                        "amount": 450000,
                        "status": "success",
                        "paid_at": "2026-04-18T12:00:00.000Z",
                        "currency": "NGN",
                        "customer": {"email": "john@example.com"},
                    },
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        paystack_signature = request.headers.get("x-paystack-signature", "")
        raw_body = request.body

        expected = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode("utf-8"),
            raw_body,
            hashlib.sha512,
        ).hexdigest()

        if not hmac.compare_digest(expected, paystack_signature):
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            return Response({"detail": "Bad JSON."}, status=status.HTTP_400_BAD_REQUEST)

        event = payload.get("event")
        data = payload.get("data", {})
        reference = data.get("reference")

        if event == "charge.success" and reference:
            try:
                checkout_service.handle_payment_verification(reference)
            except Exception:
                logger.exception("Webhook verification failed for reference: %s", reference)

        return Response({"status": "ok"}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────
#  ORDER HISTORY
# ─────────────────────────────────────────────────

class MyOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Orders"],
        summary="List my orders",
        description=(
            "Returns all orders placed by the currently authenticated user, newest first. "
            "Each order includes its line items, payment status, and transaction reference."
        ),
        responses={
            200: OpenApiResponse(
                response=OrderSerializer(many=True),
                description="List of the authenticated user's orders.",
            ),
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
        examples=[
            OpenApiExample(
                name="200 — Order list",
                value=[
                    {
                        "id": 12,
                        "buyer_name": "John Doe",
                        "buyer_email": "john@example.com",
                        "buyer_phone": "08012345678",
                        "order_type": "PRODUCT",
                        "total_amount": "4500.00",
                        "discount_amount": "500.00",
                        "address": "12 Marina Street",
                        "city": "Lagos",
                        "state": "Lagos",
                        "country": "Nigeria",
                        "postal_code": "100001",
                        "booking_date": None,
                        "booking_time": None,
                        "booking_notes": None,
                        "status": "PAID",
                        "transaction_reference": "TXN-ABCDEF12345678",
                        "payment_status": "SUCCESS",
                        "created_at": "2026-04-18T12:00:00Z",
                        "items": [
                            {
                                "id": 1,
                                "product": 3,
                                "product_name": "Blue Sneakers",
                                "service": None,
                                "service_name": None,
                                "quantity": 2,
                                "price": "1500.00",
                                "subtotal": "3000.00",
                            }
                        ],
                    }
                ],
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request):
        orders = (
            Order.objects.filter(buyer=request.user)
            .prefetch_related("items__product", "items__service")
            .select_related("transaction")
            .order_by("-created_at")
        )
        data = OrderSerializer(orders, many=True).data
        return Response(data)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Orders"],
        summary="Get a single order",
        description=(
            "Returns a single order belonging to the authenticated user. "
            "Includes all line items, booking details (for services), "
            "shipping address (for products), and full transaction info."
        ),
        parameters=[
            OpenApiParameter(
                name="pk",
                location=OpenApiParameter.PATH,
                description="Order ID",
                required=True,
                type=OpenApiTypes.INT,
            )
        ],
        responses={
            200: OpenApiResponse(
                response=OrderSerializer,
                description="Order detail.",
            ),
            401: OpenApiResponse(description="Not authenticated."),
            404: OpenApiResponse(description="Order not found or does not belong to this user."),
        },
        examples=[
            OpenApiExample(
                name="200 — Service order detail",
                value={
                    "id": 13,
                    "buyer_name": "Jane Doe",
                    "buyer_email": "jane@example.com",
                    "buyer_phone": "08087654321",
                    "order_type": "SERVICE",
                    "total_amount": "15000.00",
                    "discount_amount": "3000.00",
                    "address": None,
                    "city": None,
                    "state": None,
                    "country": None,
                    "postal_code": None,
                    "booking_date": "2026-05-10",
                    "booking_time": "14:30:00",
                    "booking_notes": "Please bring your own tools.",
                    "status": "PAID",
                    "transaction_reference": "TXN-XYZ789ABCDEF01",
                    "payment_status": "SUCCESS",
                    "created_at": "2026-04-18T10:00:00Z",
                    "items": [
                        {
                            "id": 2,
                            "product": None,
                            "product_name": None,
                            "service": 5,
                            "service_name": "Home Cleaning",
                            "quantity": 1,
                            "price": "15000.00",
                            "subtotal": "15000.00",
                        }
                    ],
                },
                response_only=True,
                status_codes=["200"],
            ),
            OpenApiExample(
                name="200 — Product order detail",
                value={
                    "id": 12,
                    "buyer_name": "John Doe",
                    "buyer_email": "john@example.com",
                    "order_type": "PRODUCT",
                    "total_amount": "4500.00",
                    "discount_amount": "500.00",
                    "address": "12 Marina Street",
                    "city": "Lagos",
                    "state": "Lagos",
                    "country": "Nigeria",
                    "postal_code": "100001",
                    "booking_date": None,
                    "booking_time": None,
                    "booking_notes": None,
                    "status": "PAID",
                    "transaction_reference": "TXN-ABCDEF12345678",
                    "payment_status": "SUCCESS",
                    "created_at": "2026-04-18T12:00:00Z",
                    "items": [
                        {
                            "id": 1,
                            "product": 3,
                            "product_name": "Blue Sneakers",
                            "service": None,
                            "service_name": None,
                            "quantity": 2,
                            "price": "1500.00",
                            "subtotal": "3000.00",
                        }
                    ],
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def get(self, request, pk):
        try:
            order = (
                Order.objects.prefetch_related("items__product", "items__service")
                .select_related("transaction")
                .get(pk=pk, buyer=request.user)
            )
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        data = OrderSerializer(order).data
        return Response(data)