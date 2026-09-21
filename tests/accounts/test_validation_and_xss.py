from django.test import TestCase
from django.urls import reverse

from accounts.models import User


class AccountValidationAndXssTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile-user",
            email="profile@example.com",
            password="SecurePass123!",
        )

    def test_profile_rejects_duplicate_email(self):
        User.objects.create_user(
            username="other-user",
            email="other@example.com",
            password="SecurePass123!",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("profile"),
            {
                "username": self.user.username,
                "first_name": "",
                "last_name": "",
                "email": "OTHER@EXAMPLE.COM",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)

    def test_profile_values_are_escaped_in_html(self):
        self.client.force_login(self.user)
        payload = "<script>alert(1)</script>"

        response = self.client.post(
            reverse("profile"),
            {
                "username": self.user.username,
                "first_name": payload,
                "last_name": "",
                "email": self.user.email,
            },
        )

        self.assertRedirects(response, reverse("profile"))
        page = self.client.get(reverse("profile"))
        self.assertNotContains(page, payload, html=False)
        self.assertContains(page, "&lt;script&gt;", html=False)
