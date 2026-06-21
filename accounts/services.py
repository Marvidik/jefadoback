import random
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from accounts.models import PasswordResetOTP
from core.email_service import send_jefedo_email

class AuthService:

    @staticmethod
    def create_password_reset_otp(user):
        otp = str(random.randint(100000, 999999))

        PasswordResetOTP.objects.create(
            user=user,
            otp=otp
        )
        
        send_jefedo_email(
            to_email=user.email,
            subject="Your Password Reset OTP",
            template_name="auth/otp_email.html",
            context={"otp": otp}
        )
       
        return otp