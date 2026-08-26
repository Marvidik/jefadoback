import secrets
import string
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .constants import (
    REFERRAL_CODE_LENGTH,
    REFERRAL_MINIMUM_FUNDING,
    REFERRAL_REWARD,
    REFERRAL_REWARD_TYPE,
)
from .models import Referral, ReferralCode


class ReferralService:

    @staticmethod
    def get_client_ip(request):
        if not request:
            return None

        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        return request.META.get("REMOTE_ADDR")

    @staticmethod
    def generate_code():
        alphabet = string.ascii_uppercase + string.digits

        while True:
            code = "".join(
                secrets.choice(alphabet)
                for _ in range(REFERRAL_CODE_LENGTH)
            )

            if not ReferralCode.objects.filter(code=code).exists():
                return code

    @staticmethod
    @transaction.atomic
    def get_or_create_code(user):
        existing = (
            ReferralCode.objects
            .select_for_update()
            .filter(user=user)
            .first()
        )

        if existing:
            return existing

        return ReferralCode.objects.create(
            user=user,
            code=ReferralService.generate_code(),
        )

    @staticmethod
    @transaction.atomic
    def create_referral(user, code, request=None):
        code = (code or "").strip().upper()

        if not code:
            raise ValueError("Referral code is required.")

        referral_code = (
            ReferralCode.objects
            .select_related("user")
            .filter(
                code=code,
                is_active=True,
            )
            .first()
        )

        if not referral_code:
            raise ValueError("Invalid or inactive referral code.")

        referrer = referral_code.user

        if referrer.pk == user.pk:
            raise ValueError("You cannot use your own referral code.")

        existing = Referral.objects.filter(
            referred_user=user,
        ).first()

        if existing:
            raise ValueError(
                "This account has already used a referral code."
            )

        signup_ip = ReferralService.get_client_ip(request)

        user_agent = ""

        if request:
            user_agent = request.META.get(
                "HTTP_USER_AGENT",
                "",
            )[:5000]

        risk_score = 0
        risk_reasons = []

        # Same phone is a strong fraud signal.
        if referrer.phone and user.phone:
            referrer_phone = (
                str(referrer.phone)
                .replace(" ", "")
                .replace("-", "")
                .strip()
            )

            referred_phone = (
                str(user.phone)
                .replace(" ", "")
                .replace("-", "")
                .strip()
            )

            if referrer_phone and referred_phone:
                if referrer_phone == referred_phone:
                    risk_score += 100
                    risk_reasons.append(
                        "Referrer and referred user have the same phone number."
                    )

        # Same IP is not automatically fraud because families/offices
        # can share an IP. It therefore goes to review rather than rejection.
        if signup_ip:
            previous_same_ip = Referral.objects.filter(
                referrer=referrer,
                signup_ip=signup_ip,
            ).exists()

            if previous_same_ip:
                risk_score += 40
                risk_reasons.append(
                    "Multiple referrals from the same IP address."
                )

        # A user already having referrals from the same IP is suspicious.
        if signup_ip:
            same_ip_count = Referral.objects.filter(
                signup_ip=signup_ip,
            ).count()

            if same_ip_count >= 3:
                risk_score += 30
                risk_reasons.append(
                    "High number of referrals from the same IP address."
                )

        if risk_score >= 100:
            status = Referral.Status.REJECTED
            rejection_reason = (
                "Referral failed fraud checks."
            )
        elif risk_score >= 40:
            status = Referral.Status.REVIEW
            rejection_reason = ""
        else:
            status = Referral.Status.PENDING
            rejection_reason = ""

        referral = Referral.objects.create(
            referrer=referrer,
            referred_user=user,
            referral_code=referral_code,
            status=status,
            signup_ip=signup_ip,
            signup_user_agent=user_agent,
            risk_score=risk_score,
            risk_reasons=risk_reasons,
            rejection_reason=rejection_reason,
        )

        return referral

    @staticmethod
    def get_user_referral(user):
        return (
            Referral.objects
            .select_related(
                "referrer",
                "referred_user",
                "referral_code",
            )
            .filter(
                referred_user=user,
            )
            .first()
        )

    @staticmethod
    def get_referral_stats(user):
        referral_code = ReferralService.get_or_create_code(user)

        referrals = Referral.objects.filter(
            referrer=user,
        )

        rewarded = referrals.filter(
            status=Referral.Status.REWARDED,
        )

        pending_count = Referral.objects.filter(
            referrer=user,
            status=Referral.Status.PENDING,
        ).count()


        total_earned = (
            rewarded.count() * REFERRAL_REWARD
        )

        return {
            "code": referral_code.code,
            "total_referrals": referrals.count(),
            "successful_referrals": rewarded.count(),
            "pending_referrals": pending_count,
            "total_earned": total_earned,
            "reward_per_referral": REFERRAL_REWARD,
            "minimum_funding": REFERRAL_MINIMUM_FUNDING,
        }

    @staticmethod
    @transaction.atomic
    def check_and_qualify(user):
        """
        Called after a successful wallet funding.

        Only the referred user's FIRST successful qualifying funding
        can trigger the referral.

        Once REWARDED, this referral is permanently finished.
        """

        referral = (
            Referral.objects
            .select_for_update()
            .select_related(
                "referrer",
                "referred_user",
            )
            .filter(
                referred_user=user,
            )
            .first()
        )

        if not referral:
            return None

        if referral.status == Referral.Status.REWARDED:
            return referral

        if referral.status in [
            Referral.Status.REJECTED,
            Referral.Status.REVIEW,
        ]:
            return referral

        from wallets.models import WalletTransaction

        total_successful_funding = (
            WalletTransaction.objects
            .filter(
                wallet__user=user,
                type="FUNDING",
                direction="CREDIT",
                status="SUCCESS",
            )
            .order_by("created_at")
        )

        first_funding = total_successful_funding.first()

        if not first_funding:
            return referral

        # Only the FIRST successful funding can qualify the referral.
        if first_funding.amount < REFERRAL_MINIMUM_FUNDING:
            return referral

        referral.status = Referral.Status.QUALIFIED
        referral.qualified_at = timezone.now()

        referral.save(
            update_fields=[
                "status",
                "qualified_at",
                "updated_at",
            ]
        )

        return ReferralService.reward_referral(referral)

    @staticmethod
    @transaction.atomic
    def reward_referral(referral):
        """
        Pays exactly once.

        The references are deterministic:
            REF-{referral_id}-REFERRER
            REF-{referral_id}-REFERRED

        WalletService.credit() is itself idempotent, so even if this
        method is accidentally called more than once, the wallets
        cannot receive duplicate rewards.
        """

        referral = (
            Referral.objects
            .select_for_update()
            .select_related(
                "referrer",
                "referred_user",
            )
            .get(pk=referral.pk)
        )

        if referral.status == Referral.Status.REWARDED:
            return referral

        if referral.status != Referral.Status.QUALIFIED:
            raise ValueError(
                "Referral must be qualified before it can be rewarded."
            )

        # Local import prevents circular imports.
        from wallets.services import WalletService

        referrer_wallet = WalletService.get_or_create_wallet(
            referral.referrer,
        )

        referred_wallet = WalletService.get_or_create_wallet(
            referral.referred_user,
        )

        referrer_reference = (
            f"REF-{referral.id}-REFERRER"
        )

        referred_reference = (
            f"REF-{referral.id}-REFERRED"
        )

        WalletService.credit(
            wallet=referrer_wallet,
            amount=REFERRAL_REWARD,
            type=REFERRAL_REWARD_TYPE,
            reference=referrer_reference,
            description="Referral reward for successful referral.",
            metadata={
                "referral_id": str(referral.id),
                "role": "referrer",
                "referrer_user_id": referral.referrer_id,
                "referred_user_id": referral.referred_user_id,
            },
        )

        WalletService.credit(
            wallet=referred_wallet,
            amount=REFERRAL_REWARD,
            type=REFERRAL_REWARD_TYPE,
            reference=referred_reference,
            description="Welcome reward for joining through a referral.",
            metadata={
                "referral_id": str(referral.id),
                "role": "referred",
                "referrer_user_id": referral.referrer_id,
                "referred_user_id": referral.referred_user_id,
            },
        )

        referral.status = Referral.Status.REWARDED
        referral.rewarded_at = timezone.now()

        referral.save(
            update_fields=[
                "status",
                "rewarded_at",
                "updated_at",
            ]
        )

        return referral
