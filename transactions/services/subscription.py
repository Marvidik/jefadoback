# transactions/services/subscription.py

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from transactions.models import (
    Plan,
    PlanPayment,
    UserSubscription,
)

from .paystack import (
    generate_reference,
    initialize_transaction,
    verify_transaction,
)


class SubscriptionService:

    @staticmethod
    @transaction.atomic
    def initialize_plan_payment(user, plan_slug):

        plan = Plan.objects.filter(
            slug=plan_slug,
            is_active=True,
        ).first()

        if not plan:
            raise ValueError("Plan not found.")

        reference = generate_reference()

        metadata = {
            "user_id": user.id,
            "plan_slug": plan.slug,
            "payment_type": "subscription",
        }

        paystack_response = initialize_transaction(
            email=user.email,
            amount_naira=float(plan.price),
            reference=reference,
            metadata=metadata,
        )

        payment = PlanPayment.objects.create(
            user=user,
            plan=plan,
            amount=plan.price,
            reference=reference,
            paystack_access_code=paystack_response.get("access_code"),
            paystack_authorization_url=paystack_response.get("authorization_url"),
            status=PlanPayment.STATUS_PENDING,
            raw_response=paystack_response,
        )

        return {
            "payment_id": str(payment.id),
            "authorization_url": paystack_response.get("authorization_url"),
            "access_code": paystack_response.get("access_code"),
            "reference": reference,
        }

    @staticmethod
    @transaction.atomic
    def verify_plan_payment(reference):

        payment = (
            PlanPayment.objects
            .select_for_update()
            .select_related("user", "plan")
            .filter(reference=reference)
            .first()
        )

        if not payment:
            raise ValueError("Payment not found.")

        if payment.status == PlanPayment.STATUS_SUCCESS:

            subscription = (
                UserSubscription.objects
                .filter(
                    user=payment.user,
                    plan=payment.plan,
                    status=UserSubscription.STATUS_ACTIVE,
                )
                .order_by("-created_at")
                .first()
            )

            return {
                "message": "Payment already verified.",
                "reference": payment.reference,
                "subscription_id": subscription.id if subscription else None,
            }

        verification_data = verify_transaction(reference)

        payment.raw_response = verification_data

        gateway_status = verification_data.get("status")

        if gateway_status != "success":

            payment.status = PlanPayment.STATUS_FAILED

            payment.save(
                update_fields=[
                    "status",
                    "raw_response",
                ]
            )

            raise ValueError("Payment was not successful.")

        amount_paid = (
            Decimal(str(verification_data.get("amount", 0)))
            / Decimal("100")
        )

        if amount_paid != payment.amount:

            payment.status = PlanPayment.STATUS_FAILED

            payment.save(update_fields=["status"])

            raise ValueError("Invalid payment amount detected.")

        payment.status = PlanPayment.STATUS_SUCCESS

        payment.paid_at = timezone.now()

        payment.save(
            update_fields=[
                "status",
                "paid_at",
                "raw_response",
            ]
        )

        UserSubscription.objects.filter(
            user=payment.user,
            status=UserSubscription.STATUS_ACTIVE,
        ).update(
            status=UserSubscription.STATUS_EXPIRED
        )

        start_date = timezone.now()

        end_date = (
            start_date +
            timedelta(days=payment.plan.duration_days)
        )

        subscription = UserSubscription.objects.create(
            user=payment.user,
            plan=payment.plan,
            start_date=start_date,
            end_date=end_date,
            status=UserSubscription.STATUS_ACTIVE,
        )

        return {
            "message": "Subscription activated successfully.",
            "subscription_id": subscription.id,
            "reference": payment.reference,
            "plan": payment.plan.name,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
        }