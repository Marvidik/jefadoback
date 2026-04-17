from django.db import models
from django.utils import timezone


# Create your models here.
class Order(models.Model):

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

    # 👤 Buyer snapshot (important for history integrity)
    buyer_name = models.CharField(max_length=255)
    buyer_email = models.EmailField()
    buyer_phone = models.CharField(max_length=20, blank=True, null=True)

    
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)

  
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    # 🧠 Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)




class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    # Product or Service reference (flexible design)
    product = models.ForeignKey(
        "sellers.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items"
    )

    service = models.ForeignKey(
        "sellers.Service",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items"
    )

    quantity = models.PositiveIntegerField(default=1)

    price = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        # ensure only one is used
        if self.product and self.service:
            raise ValueError("OrderItem can only have product OR service")
        


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