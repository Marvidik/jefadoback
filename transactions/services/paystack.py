"""
payments/paystack.py
Thin wrapper around the Paystack REST API.
Set PAYSTACK_SECRET_KEY in your Django settings or environment.
"""
import uuid
import logging

import requests
from requests.exceptions import ConnectionError, Timeout, RequestException

from django.conf import settings

logger = logging.getLogger(__name__)

PAYSTACK_BASE_URL = "https://api.paystack.co"


def _headers():
    key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
    if not key or key == "sk_test_xxxxxxxxxxxx":
        raise ValueError(
            "PAYSTACK_SECRET_KEY is not configured. "
            "Set it in your settings or environment variables."
        )
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def generate_reference() -> str:
    """Generate a unique transaction reference."""
    return f"TXN-{uuid.uuid4().hex.upper()[:16]}"


def initialize_transaction(
    email: str,
    amount_naira: float,
    reference: str,
    metadata: dict = None,
) -> dict:
    """
    Initialize a Paystack transaction.
    Amount must be in Naira — this function converts to kobo (×100).

    Returns: { authorization_url, access_code, reference }
    Raises ValueError on Paystack rejection or config error.
    Raises RuntimeError on network / unexpected errors.
    """
    payload = {
        "email": email,
        "amount": int(amount_naira * 100),  # kobo
        "reference": reference,
        "currency": "NGN",
    }

    callback_url = getattr(settings, "PAYSTACK_CALLBACK_URL", None)
    if callback_url:
        payload["callback_url"] = callback_url

    if metadata:
        payload["metadata"] = metadata

    logger.info("Initialising Paystack transaction: ref=%s email=%s amount=%.2f", reference, email, amount_naira)

    try:
        response = requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            json=payload,
            headers=_headers(),
            timeout=30,
        )
    except Timeout:
        raise RuntimeError("Paystack did not respond in time. Please try again.")
    except ConnectionError:
        raise RuntimeError("Could not connect to Paystack. Check your internet connection.")
    except RequestException as e:
        raise RuntimeError(f"Network error reaching Paystack: {e}")

    # Parse response safely
    try:
        data = response.json()
    except Exception:
        raise RuntimeError(
            f"Paystack returned an unexpected response (HTTP {response.status_code}). "
            f"Body: {response.text[:300]}"
        )

    logger.debug("Paystack init response: %s", data)

    if not data.get("status"):
        # Paystack rejected — surface their message as a user-facing error
        raise ValueError(data.get("message", "Paystack rejected the transaction initialisation."))

    payload_data = data.get("data")
    if not payload_data or "authorization_url" not in payload_data:
        raise RuntimeError(
            f"Paystack response missing 'data.authorization_url'. Got: {data}"
        )

    return payload_data  # { authorization_url, access_code, reference }


def verify_transaction(reference: str) -> dict:
    """
    Verify a Paystack transaction by reference.

    Returns the full Paystack transaction data dict.
    Raises ValueError on Paystack rejection or config error.
    Raises RuntimeError on network / unexpected errors.
    """
    logger.info("Verifying Paystack transaction: ref=%s", reference)

    try:
        response = requests.get(
            f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}",
            headers=_headers(),
            timeout=30,
        )
    except Timeout:
        raise RuntimeError("Paystack did not respond in time during verification.")
    except ConnectionError:
        raise RuntimeError("Could not connect to Paystack for verification.")
    except RequestException as e:
        raise RuntimeError(f"Network error during Paystack verification: {e}")

    try:
        data = response.json()
    except Exception:
        raise RuntimeError(
            f"Paystack verification returned unexpected response (HTTP {response.status_code}). "
            f"Body: {response.text[:300]}"
        )

    logger.debug("Paystack verify response: %s", data)

    if not data.get("status"):
        raise ValueError(data.get("message", "Paystack verification failed."))

    payload_data = data.get("data")
    if not payload_data:
        raise RuntimeError(f"Paystack verify response missing 'data'. Got: {data}")

    return payload_data