import secrets
import string
from datetime import timedelta

from django.utils import timezone

from accounts.models import PasswordResetOTP, LoginOTP
from core.email_service import send_jefedo_email

OTP_EXPIRY_MINUTES = 5


def _generate_otp(length=4):
    return ''.join(secrets.choice(string.digits) for _ in range(length))


class AuthService:

    @staticmethod
    def create_password_reset_otp(user):
        otp = _generate_otp()  # generated fresh, per call

        PasswordResetOTP.objects.create(user=user, otp=otp)

        send_jefedo_email(
            to_email=user.email,
            subject="Your Password Reset OTP",
            template_name="auth/otp_email.html",
            context={"otp": otp}
        )
        return otp

    @staticmethod
    def create_and_send_login_otp(user):
        otp = _generate_otp()

        LoginOTP.objects.create(user=user, otp=otp)

        send_jefedo_email(
            to_email=user.email,
            subject="Your Login Verification Code",
            template_name="auth/otp_email.html",
            context={
                "otp": otp,
                "name": user.first_name or user.email.split('@')[0],
            }
        )
        return otp

    @staticmethod
    def verify_login_otp(user, otp):
        """Returns (is_valid, error_message)."""
        cutoff = timezone.now() - timedelta(minutes=OTP_EXPIRY_MINUTES)

        record = LoginOTP.objects.filter(
            user=user, otp=otp, is_used=False, created_at__gte=cutoff
        ).order_by('-created_at').first()

        if not record:
            return False, "Invalid or expired code."

        record.is_used = True
        record.save(update_fields=['is_used'])
        return True, None