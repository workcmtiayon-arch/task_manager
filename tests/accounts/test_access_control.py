from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class AccountAccessControlTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="SecurePass123!",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="SecurePass123!",
        )
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="SecurePass123!",
            role=User.Role.ADMIN,
        )

    def test_private_account_pages_require_authentication(self):
        for name in ("dashboard", "profile", "user_list"):
            response = self.client.get(reverse(name))
            self.assertRedirects(
                response,
                f"{reverse('login')}?next={reverse(name)}",
            )

    def test_non_admin_cannot_list_or_toggle_users(self):
        self.client.force_login(self.user)

        self.assertEqual(self.client.get(reverse("user_list")).status_code, 403)
        response = self.client.post(
            reverse("toggle_user_status", args=[self.other_user.pk]),
        )

        self.assertEqual(response.status_code, 403)
        self.other_user.refresh_from_db()
        self.assertTrue(self.other_user.is_active)

    def test_admin_cannot_disable_own_account(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("toggle_user_status", args=[self.admin.pk]),
        )

        self.assertRedirects(response, reverse("user_list"))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_external_login_redirect_is_rejected(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": self.user.username,
                "password": "SecurePass123!",
                "next": "https://evil.example/phishing",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
