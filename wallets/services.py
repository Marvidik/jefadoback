
import logging
from decimal import Decimal

from django.db import transaction as db_transaction

from .models import Wallet, WalletTransaction

logger = logging.getLogger(__name__)


class InsufficientBalanceError(Exception):
    pass


class WalletFrozenError(Exception):
    pass


class WalletService:

    @staticmethod
    def get_or_create_wallet(user, currency="NGN"):
        wallet, _ = Wallet.objects.get_or_create(user=user, defaults={"currency": currency})
        return wallet

    # ── IMMEDIATE (synchronous) entries — purchases, refunds, admin ────────
    # Used when there's no external gateway round-trip: the money movement
    # is fully internal and can be applied in one atomic step.

    @staticmethod
    @db_transaction.atomic
    def credit(wallet, amount, type, reference, order=None, description="", metadata=None):
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Credit amount must be positive.")

        existing = WalletTransaction.objects.filter(reference=reference).first()
        if existing:
            return existing  # idempotent — same reference, no double-credit

        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if wallet.status != "ACTIVE" and type != "ADMIN_ADJUSTMENT":
            raise WalletFrozenError(f"Wallet is {wallet.status.lower()}; cannot credit.")

        balance_before = wallet.balance
        balance_after = balance_before + amount
        wallet.balance = balance_after
        wallet.save(update_fields=["balance", "updated_at"])

        return WalletTransaction.objects.create(
            wallet=wallet, reference=reference, type=type, direction="CREDIT",
            amount=amount, balance_before=balance_before, balance_after=balance_after,
            status="SUCCESS", order=order, description=description, metadata=metadata or {},
        )

    @staticmethod
    @db_transaction.atomic
    def debit(wallet, amount, type, reference, order=None, description="", metadata=None):
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Debit amount must be positive.")

        existing = WalletTransaction.objects.filter(reference=reference).first()
        if existing:
            return existing

        # select_for_update() locks this row until commit — a second
        # concurrent debit request has to wait, so it sees the updated
        # balance instead of the stale one. This is what stops the
        # double-spend scenario in the email above.
        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        if wallet.status != "ACTIVE":
            raise WalletFrozenError(f"Wallet is {wallet.status.lower()}; cannot debit.")
        if wallet.balance < amount:
            raise InsufficientBalanceError("Insufficient wallet balance.")

        balance_before = wallet.balance
        balance_after = balance_before - amount
        wallet.balance = balance_after
        wallet.save(update_fields=["balance", "updated_at"])

        return WalletTransaction.objects.create(
            wallet=wallet, reference=reference, type=type, direction="DEBIT",
            amount=amount, balance_before=balance_before, balance_after=balance_after,
            status="SUCCESS", order=order, description=description, metadata=metadata or {},
        )

    # ── TWO-PHASE entries — wallet funding via Paystack ─────────────────────
    # Phase 1 creates a PENDING ledger row with NO balance change (we can't
    # trust the frontend saying "payment succeeded" — see the email).
    # Phase 2 runs from either the verify endpoint or the webhook, whichever
    # arrives first; complete_funding() is idempotent either way.

    @staticmethod
    def initiate_funding(wallet, amount, reference, gateway_reference=None):
        amount = Decimal(str(amount))
        return WalletTransaction.objects.create(
            wallet=wallet, reference=reference, type="FUNDING", direction="CREDIT",
            amount=amount, status="PENDING", gateway_reference=gateway_reference,
            description="Wallet funding via Paystack",
        )

    @staticmethod
    @db_transaction.atomic
    def complete_funding(reference):
        txn = WalletTransaction.objects.select_for_update().get(reference=reference)

        if txn.status == "SUCCESS":
            return txn  # already processed — Paystack retried the webhook, ignore

        if txn.status != "PENDING":
            raise ValueError(f"Cannot complete funding — transaction is {txn.status}.")

        wallet = Wallet.objects.select_for_update().get(pk=txn.wallet_id)

        balance_before = wallet.balance
        balance_after = balance_before + txn.amount
        wallet.balance = balance_after
        wallet.save(update_fields=["balance", "updated_at"])

        txn.status = "SUCCESS"
        txn.balance_before = balance_before
        txn.balance_after = balance_after
        txn.save(update_fields=["status", "balance_before", "balance_after", "updated_at"])
        return txn

    @staticmethod
    @db_transaction.atomic
    def fail_funding(reference, reason=""):
        txn = WalletTransaction.objects.select_for_update().get(reference=reference)
        if txn.status == "SUCCESS":
            return txn  # never downgrade a completed credit
        txn.status = "FAILED"
        txn.description = reason or txn.description
        txn.save(update_fields=["status", "description", "updated_at"])
        return txn

    # ── Refunds & reversals — never edit the original row ───────────────────

    @staticmethod
    def refund(original_txn, amount=None, description=""):
        if original_txn.direction != "DEBIT":
            raise ValueError("Can only refund a DEBIT transaction.")
        refund_amount = Decimal(str(amount)) if amount else original_txn.amount
        return WalletService.credit(
            wallet=original_txn.wallet, amount=refund_amount, type="REFUND",
            reference=f"RFD-{original_txn.reference}", order=original_txn.order,
            description=description or f"Refund for {original_txn.reference}",
            metadata={"original_transaction": original_txn.reference},
        )

    @staticmethod
    def reverse(original_txn, description=""):
        reference = f"REV-{original_txn.reference}"
        if original_txn.direction == "CREDIT":
            return WalletService.debit(
                wallet=original_txn.wallet, amount=original_txn.amount, type="ADMIN_ADJUSTMENT",
                reference=reference, description=description or f"Reversal of {original_txn.reference}",
                metadata={"original_transaction": original_txn.reference},
            )
        return WalletService.credit(
            wallet=original_txn.wallet, amount=original_txn.amount, type="ADMIN_ADJUSTMENT",
            reference=reference, description=description or f"Reversal of {original_txn.reference}",
            metadata={"original_transaction": original_txn.reference},
        )