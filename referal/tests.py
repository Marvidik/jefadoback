from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.test import TestCase

from .models import Referral, ReferralCode


class ClaimReferralTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.referrer = get_user_model().objects.create_user(
            email="referrer@example.com",
            password="test-password",
        )
        self.referral_code = ReferralCode.objects.create(
            user=self.referrer,
            code="FRIEND123",
        )

    def claim_referral(self, email):
        user = get_user_model().objects.create_user(
            email=email,
            password="test-password",
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            "/api/v1/referrals/claim/",
            {"referral_code": self.referral_code.code},
            format="json",
        )
        return user, response

    def test_claim_creates_referral_with_code_and_risk_fields(self):
        user, response = self.claim_referral("referred@example.com")

        self.assertEqual(response.status_code, 201)
        referral = Referral.objects.get(referred_user=user)
        self.assertEqual(referral.referral_code, self.referral_code)
        self.assertEqual(referral.status, Referral.Status.PENDING)
        self.assertEqual(referral.risk_score, 0)
        self.assertEqual(referral.risk_reasons, [])

    def test_repeat_referrer_ip_sets_review_status_and_risk_details(self):
        _, first_response = self.claim_referral("first@example.com")
        self.assertEqual(first_response.status_code, 201)

        second_user, second_response = self.claim_referral("second@example.com")

        self.assertEqual(second_response.status_code, 201)
        referral = Referral.objects.get(referred_user=second_user)
        self.assertEqual(referral.status, Referral.Status.REVIEW)
        self.assertEqual(referral.risk_score, 40)
        self.assertIn(
            "Multiple referrals from the same IP address.",
            referral.risk_reasons,
        )
