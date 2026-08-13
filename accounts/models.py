import secrets

from django.db import models
from django.contrib.auth.models import AbstractUser
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
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