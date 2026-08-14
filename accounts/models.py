import secrets

from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from django.utils import timezone


# Create your models here.

class User(AbstractUser):

    class Role(models.TextChoices):
        MEMBER = "MEMBER", "member"
        ADMIN = "ADMIN", "admin"
    role = models.CharField(max_length=15, choices=Role.choices, default=Role.MEMBER)
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)

    # username = models.CharField(max_length=50)
    # password = models.CharField()
    # date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class EmailOTP(models.Model):

    class Purpose(models.TextChoices):
        REGISTER = "REGISTER", "Verification d'inscription"
        PASSWORD_RESET = "PASSWORD_RESET", "Reinitialisation du mot de passe"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otps")
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    @classmethod
    def generate_for(cls, user, purpose):

        from django.conf import settings as dj_settings

        cls.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)
        code = f"{secrets.randbelow(1_000_000):06d}"
        ttl = getattr(dj_settings, "OTP_TTL_MINUTES", 10)
        opt = cls.objects.create(user=user, purpose=purpose, code_hash=make_password(code), expires_at=timezone.now() + timedelta(minutes=ttl))

        return opt, code

    def is_valid(self):

        from django.conf import settings as dj_settings

        max_attempts = getattr(dj_settings, "OTP_MAX_ATTEMPTS", 5)
        return (
            not self.is_used
            and self.attempts < max_attempts
            and timezone.now() <= self.expires_at
        )

    def check_email(self, submitted_code):

        if not self.is_valid():
            return False
        self.attempts += 1
        ok = check_password(submitted_code, self.code_hash)

        if ok:
            self.is_used = True

        self.save(update_fields=["attempts", "is_used"])
        return ok