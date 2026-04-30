from django.shortcuts import get_object_or_404
from decimal import Decimal
from transactions.models import PayoutRequest, BankAccount, Order
from django.db.models import Sum,Q

class PayoutService:

    @staticmethod
    def get_total_earnings(seller):
        return (
            Order.objects.filter(
                Q(items__product__seller=seller) |
                Q(items__service__seller=seller),
                status="COMPLETED"
            )
            .distinct()
            .aggregate(total=Sum("total_amount"))
            .get("total") or Decimal("0.00")
        )

    @staticmethod
    def get_total_pending_and_successful_payouts(seller):
        return (
            PayoutRequest.objects.filter(
                seller=seller,
                status__in=["PENDING", "PROCESSING", "SUCCESS"]
            )
            .aggregate(total=Sum("amount"))
            .get("total") or Decimal("0.00")
        )

    @classmethod
    def get_available_balance(cls, seller):
        return cls.get_total_earnings(seller) - cls.get_total_pending_and_successful_payouts(seller)


    @classmethod
    def get_cards(cls, seller):

        earned = cls.get_total_earnings(seller)

        payouts = cls.get_total_pending_and_successful_payouts(
            seller
        )

        balance = earned - payouts

        return {
            "total_earned": earned,
            "payouts": payouts,
            "available_balance": balance
        }

    @staticmethod
    def list_requests(seller):
        return (
            PayoutRequest.objects.filter(seller=seller)
            .select_related("bank_account")
            .order_by("-created_at")
        )

    @classmethod
    def create_request(cls, seller, data):

        bank_account = data.get("bank_account")
        amount = Decimal(str(data.get("amount", 0)))

        
        if isinstance(bank_account, BankAccount):
            bank_account_id = bank_account.id
        else:
            bank_account_id = bank_account

        bank_account_obj = get_object_or_404(
            BankAccount,
            id=bank_account_id,
            seller=seller
        )

        if amount <= 0:
            raise ValueError("Invalid withdrawal amount")

        available_balance = cls.get_available_balance(seller)

        if amount > available_balance:
            raise ValueError("Insufficient balance")

        return PayoutRequest.objects.create(
            seller=seller,
            bank_account=bank_account_obj,
            amount=amount,
            status="PENDING"
        )

    @staticmethod
    def delete_request(request_id, seller):
        req = get_object_or_404(
            PayoutRequest,
            id=request_id,
            seller=seller
        )
        req.delete()
        return True