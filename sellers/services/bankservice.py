from django.shortcuts import get_object_or_404
from transactions.models import BankAccount


class BankAccountService:

    @staticmethod
    def list_accounts(seller):
        return BankAccount.objects.filter(seller=seller)

    @staticmethod
    def create_account(seller, data):
        return BankAccount.objects.create(seller=seller, **data)

    @staticmethod
    def delete_account(account_id, seller):
        account = get_object_or_404(
            BankAccount,
            id=account_id,
            seller=seller
        )
        account.delete()
        return True