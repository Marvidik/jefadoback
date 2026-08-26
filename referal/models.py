# referrals/models.py

import uuid
from django.conf import settings
from django.db import models


class ReferralCode(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_code",
    )
    code = models.CharField(max_length=20, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id} - {self.code}"


class Referral(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        QUALIFIED = "QUALIFIED", "Qualified"
        REWARDED = "REWARDED", "Rewarded"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="referrals_sent",
    )

    referred_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="referral_received",
    )

    code = models.ForeignKey(
        ReferralCode,
        on_delete=models.PROTECT,
        related_name="referrals",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Useful fraud/audit information
    signup_ip = models.GenericIPAddressField(null=True, blank=True)
    signup_user_agent = models.TextField(blank=True)

    qualified_at = models.DateTimeField(null=True, blank=True)
    rewarded_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.referrer_id} -> {self.referred_user_id}"
