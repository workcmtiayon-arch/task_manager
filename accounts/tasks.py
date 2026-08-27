from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string

User = get_user_model()

OTP_EMAIL_CONTEXT = {
    "REGISTER": {
        "subject": "Votre code de verification Task Manager",
        "template": "accounts/emails/otp_register.txt",
    },
    "PASSWORD_RESET": {
        "subject": "Votre code de Reinitialisation Task Manager",
        "template": "accounts/emails/otp_reset.txt",
    },
}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_otp_email_task(self, user_id, code, purpose):

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    config = OTP_EMAIL_CONTEXT[purpose]
    message = render_to_string(config["template"], {"username": user.username, "code": code})
    try:
        send_mail(
            subject=config["subject"],
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def send_registration_alert_email_task(email):
    message = render_to_string("accounts/emails/registration_alert.txt", {})
    send_mail(
        subject="Tentative de creation de compte Task Manager",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=True,
    )