from django.conf import settings
from django.db import models


class Wallet(models.Model):
    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("FROZEN", "Frozen"),
        ("SUSPENDED", "Suspended"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    currency = models.CharField(max_length=10, default="NGN")
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ACTIVE")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} — {self.currency} {self.balance}"


class WalletTransaction(models.Model):
    """
    The ledger. Immutable once SUCCESS — never edited, only ever
    followed by a REFUND or REVERSAL entry pointing back at it.
    """
    TYPE_CHOICES = (
        ("FUNDING", "Wallet Funding"),
        ("PURCHASE", "Purchase"),
        ("REFUND", "Refund"),
        ("WITHDRAWAL", "Withdrawal"),
        ("ADMIN_ADJUSTMENT", "Admin Adjustment"),
    )
    DIRECTION_CHOICES = (("CREDIT", "Credit"), ("DEBIT", "Debit"))
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
        ("REVERSED", "Reversed"),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    reference = models.CharField(max_length=100, unique=True)

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)

    amount = models.DecimalField(max_digits=14, decimal_places=2)
    # Null while PENDING (e.g. funding not yet confirmed by gateway).
    # Populated the instant the entry becomes SUCCESS — never touched again.
    balance_before = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    order = models.ForeignKey(
        "transactions.Order", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="wallet_transactions",
    )
    gateway_reference = models.CharField(max_length=100, blank=True, null=True)

    description = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="wallet_adjustments_made",
        help_text="Set only for ADMIN_ADJUSTMENT entries — who authorised it.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.reference} — {self.direction} {self.amount} ({self.status})"