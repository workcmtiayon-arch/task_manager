from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

User = get_user_model()


OTP_EMAIL_CONTEXT = {
    "REGISTER": {
        "subject": "Votre code de verification Task Manager",
        "text_template": "accounts/emails/otp_register.txt",
        "html_template": "accounts/emails/otp_register.html",
    },
    "PASSWORD_RESET": {
        "subject": "Votre code de Reinitialisation Task Manager",
        "text_template": "accounts/emails/otp_reset.txt",
        "html_template": "accounts/emails/otp_reset.html",
    },
}



@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_otp_email_task(self, user_id, code, purpose):

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    config = OTP_EMAIL_CONTEXT[purpose]
    context = {"username": user.username, "code": code}
    message = render_to_string(config["text_template"], context)
    html_message = render_to_string(config["html_template"], context)
    try:
        email = EmailMultiAlternatives(config["subject"], message, settings.DEFAULT_FROM_EMAIL, [user.email])
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
    except Exception as exc:
        raise self.retry(exc=exc) 



@shared_task
def send_registration_alert_email_task(email):
    context = {}
    message = render_to_string("accounts/emails/registration_alert.txt", context)
    html_message = render_to_string("accounts/emails/registration_alert.html", context)
    email_message = EmailMultiAlternatives(
        subject="Tentative de creation de compte Task Manager",
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    email_message.attach_alternative(html_message, "text/html")
    email_message.send(fail_silently=True)
