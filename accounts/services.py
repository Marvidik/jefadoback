import random
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from accounts.models import PasswordResetOTP

class AuthService:

    @staticmethod
    def create_password_reset_otp(user):
        otp = str(random.randint(100000, 999999))

        PasswordResetOTP.objects.create(
            user=user,
            otp=otp
        )
        send_mail(
            subject="Your Password Reset OTP",
            message=f"Your OTP is: {otp}. It expires in 10 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
       
        return otp