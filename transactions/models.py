from django.db import models
from django.utils import timezone



class Order(models.Model):
    buyer = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="orders",
        blank=True,
        null=True,
    )
 
    ORDER_TYPE_CHOICES = (
        ("PRODUCT", "Product"),
        ("SERVICE", "Service"),
    )
 
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PAID", "Paid"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    )
 
    buyer_name = models.CharField(max_length=255)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=20, blank=True, null=True)
 
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)
 
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
 
    # --- PRODUCT: Shipping address ---
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
 
    # --- SERVICE: Booking date & time ---
    booking_date = models.DateField(blank=True, null=True)
    booking_time = models.TimeField(blank=True, null=True)
    booking_notes = models.TextField(blank=True, null=True)
 
    coupon = models.ForeignKey(
        "Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return f"Order #{self.pk} - {self.buyer_email} ({self.order_type})"
 
 
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
 
    product = models.ForeignKey(
        "sellers.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
 
    service = models.ForeignKey(
        "sellers.Service",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
 
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
 
    def clean(self):
        if self.product and self.service:
            raise ValueError("OrderItem can only have product OR service, not both.")
        if not self.product and not self.service:
            raise ValueError("OrderItem must have either a product or a service.")
 
    def get_subtotal(self):
        return self.price * self.quantity
 
    def __str__(self):
        item = self.product or self.service
        return f"{item} x{self.quantity}"
 
        
class Transaction(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("ABANDONED", "Abandoned"),
    )
 
    order = models.OneToOneField(
        "Order",
        on_delete=models.CASCADE,
        related_name="transaction",
    )
 
    reference = models.CharField(max_length=100, unique=True)
    paystack_id = models.CharField(max_length=100, blank=True, null=True)
 
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
 
    currency = models.CharField(max_length=10, default="NGN")
 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
 
    gateway_response = models.TextField(blank=True, null=True)
    paid_at = models.DateTimeField(null=True, blank=True)
 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
 
    def __str__(self):
        return f"TXN-{self.reference} ({self.status})"
    

class Coupon(models.Model):

    DISCOUNT_TYPE = (
        ("PERCENTAGE", "Percentage"),
        ("FIXED", "Fixed"),
    )

    STATUS = (
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("USED_UP", "Used Up"),
    )

    seller = models.ForeignKey("sellers.SellerProfile", on_delete=models.CASCADE, related_name="coupons")

    code = models.CharField(max_length=50, unique=True)

    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    usage_limit = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)

    expiry_date = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    def status(self):
        if self.used_count >= self.usage_limit:
            return "USED_UP"
        if self.expiry_date < timezone.now():
            return "EXPIRED"
        return "ACTIVE"

    def __str__(self):
        return self.code



class BankAccount(models.Model):

    seller = models.ForeignKey(
        "sellers.SellerProfile",
        on_delete=models.CASCADE,
        related_name="bank_accounts"
    )

    bank_name = models.CharField(max_length=255)
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"




class PayoutRequest(models.Model):

    STATUS = (
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    )

    seller = models.ForeignKey(
        "sellers.SellerProfile",
        on_delete=models.CASCADE,
        related_name="payout_requests"
    )

    bank_account = models.ForeignKey(
        "BankAccount",
        on_delete=models.PROTECT,
        related_name="payouts"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.seller.store_name} - {self.amount}"




# subscriptions/models.py

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Plan(models.Model):
    name = models.CharField(max_length=120)

    slug = models.SlugField(unique=True)

    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    duration_days = models.PositiveIntegerField(default=30)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserSubscription(models.Model):

    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )

    start_date = models.DateTimeField()

    end_date = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_active(self):
        return (
            self.status == self.STATUS_ACTIVE
            and self.end_date > timezone.now()
        )


class PlanPayment(models.Model):

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="plan_payments",
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    reference = models.CharField(
        max_length=120,
        unique=True,
    )

    paystack_access_code = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    paystack_authorization_url = models.URLField(
        blank=True,
        null=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    paid_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    raw_response = models.JSONField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]