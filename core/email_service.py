from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from accounts.models import Notification

def send_jefedo_email(to_email, subject, template_name, context):
    """
    Renders an HTML template and sends the email.
    """
    html_message = render_to_string(f"emails/{template_name}", context)
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        html_message=html_message,
        fail_silently=False,
    )

def send_notification(user, title, message, notification_type='SYSTEM', email_template=None, email_context=None, email_subject=None):
    """
    Creates an in-app notification and optionally sends an email if template is provided.
    """
    # 1. Create In-App Notification
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type
    )

    # 2. Send Email if requested
    if email_template and email_context and email_subject:
        send_jefedo_email(
            to_email=user.email,
            subject=email_subject,
            template_name=email_template,
            context=email_context
        )
