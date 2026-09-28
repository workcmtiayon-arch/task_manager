import secrets
import os
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def profile_photo_upload_path(instance, filename):
    """Store profile photos in a per-user directory with a non-user filename."""
    extension = os.path.splitext(filename)[1].lower()
    return f"profile_photos/user_{instance.pk}/{uuid.uuid4().hex}{extension}"


def validate_profile_photo(uploaded_file):
    """Accept only small raster images whose header matches their MIME type."""
    # Model validation receives a FieldFile after the form has already
    # validated the uploaded object; the persisted wrapper has no MIME field.
    if not hasattr(uploaded_file, "content_type"):
        return
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if uploaded_file.content_type not in allowed_types:
        raise ValidationError(_("Profile photos must be JPEG, PNG, GIF or WebP images."))
    if uploaded_file.size > 5 * 1024 * 1024:
        raise ValidationError(_("Profile photos must not exceed 5 MB."))

    header = uploaded_file.read(16)
    uploaded_file.seek(0)
    signatures = {
        "image/jpeg": header.startswith(b"\xff\xd8\xff"),
        "image/png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/gif": header.startswith((b"GIF87a", b"GIF89a")),
        "image/webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
    }
    if not signatures.get(uploaded_file.content_type, False):
        raise ValidationError(_("The profile photo content does not match its type."))


# Create your models here.

class User(AbstractUser):

    class Langue(models.TextChoices):
        FRANCAIS = "fr", _("French")
        ANGLAIS = "en", _("English")

    class Role(models.TextChoices):
        MEMBER = "MEMBER", _("Member")
        ADMIN = "ADMIN", _("Administrator")
    role = models.CharField(max_length=15, choices=Role.choices, default=Role.MEMBER)
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    langue = models.CharField(max_length=5, choices=Langue.choices, default=Langue.FRANCAIS)
    profile_photo = models.FileField(
        upload_to=profile_photo_upload_path,
        blank=True,
        null=True,
        validators=[validate_profile_photo],
        verbose_name=_("Profile photo"),
    )

    # username = models.CharField(max_length=50)
    # password = models.CharField()
    # date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

    @property
    def profile_photo_url(self):
        """Return the authenticated endpoint used to display this photo."""
        if not self.profile_photo:
            return ""
        return reverse("profile_photo", args=[self.pk])


class EmailOTP(models.Model):

    class Purpose(models.TextChoices):
        REGISTER = "REGISTER", _("Registration verification")
        PASSWORD_RESET = "PASSWORD_RESET", _("Password reset")

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
        with transaction.atomic():
            otp = type(self).objects.select_for_update().get(pk=self.pk)
            if not otp.is_valid():
                return False

            otp.attempts += 1
            ok = check_password(submitted_code, otp.code_hash)
            if ok:
                otp.is_used = True
            otp.save(update_fields=["attempts", "is_used"])

            self.attempts = otp.attempts
            self.is_used = otp.is_used
            return ok
