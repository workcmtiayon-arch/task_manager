from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):

    class Role(models.TextChoices):
        MEMBER = "MEMBER", "member"
        ADMIN = "ADMIN", "admin"
    role = models.CharField(max_length=15, choices=Role.choices, default=Role.MEMBER)
    email = models.EmailField(unique=True)

    # username = models.CharField(max_length=50)
    # password = models.CharField()
    # date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
[11/Aug/2026 15:58:50] "GET /favicon.ico HTTP/1.1" 404 2978
git add .
git commit -m "new version"
git push
