from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import EmailOTP


User = get_user_model()


class OtpSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pending-user",
            email="pending@example.com",
            password="SecurePass123!",
            is_active=False,
        )
        session = self.client.session
        session["pending_user_id"] = self.user.pk
        session.save()

    @patch("accounts.views.send_otp_email_task.delay")
    def test_resend_otp_rejects_get_requests(self, send_email):
        response = self.client.get(reverse("resend-otp"))

        self.assertEqual(response.status_code, 405)
        send_email.assert_not_called()

    @patch("accounts.views.send_otp_email_task.delay")
    def test_resend_otp_requires_csrf_protection(self, send_email):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        session = csrf_client.session
        session["pending_user_id"] = self.user.pk
        session.save()

        response = csrf_client.post(reverse("resend-otp"))

        self.assertEqual(response.status_code, 403)
        send_email.assert_not_called()

    @patch("accounts.views.send_otp_email_task.delay")
    def test_resend_otp_is_rate_limited(self, send_email):
        first_response = self.client.post(reverse("resend-otp"))
        second_response = self.client.post(reverse("resend-otp"))

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(send_email.call_count, 1)

    def test_expired_otp_cannot_be_used(self):
        otp, code = EmailOTP.generate_for(self.user, EmailOTP.Purpose.REGISTER)
        otp.expires_at = timezone.now() - timedelta(seconds=1)
        otp.save(update_fields=["expires_at"])

        response = self.client.post(reverse("verify-otp"), {"code": code})

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertContains(response, "Invalid or expired code")

    def test_otp_is_single_use(self):
        otp, code = EmailOTP.generate_for(self.user, EmailOTP.Purpose.REGISTER)

        first_response = self.client.post(reverse("verify-otp"), {"code": code})
        second_response = self.client.post(reverse("verify-otp"), {"code": code})

        self.assertRedirects(first_response, reverse("login"))
        self.assertEqual(second_response.status_code, 200)
        self.assertContains(second_response, "Invalid or expired code")


class PasswordResetSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reset-user",
            email="reset@example.com",
            password="OldSecurePass123!",
        )

    def test_reset_request_does_not_enumerate_accounts(self):
        known = self.client.post(
            reverse("forgot-password"),
            {"email": self.user.email},
        )
        unknown = self.client.post(
            reverse("forgot-password"),
            {"email": "unknown@example.com"},
        )

        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known["Location"], unknown["Location"])

    def test_password_reset_invalidates_other_authenticated_sessions(self):
        existing_client = self.client_class()
        existing_client.force_login(self.user)

        session = self.client.session
        session["reset_verified_user_id"] = self.user.pk
        session.save()
        response = self.client.post(
            reverse("reset-password"),
            {
                "new_password1": "NewSecurePass123!",
                "new_password2": "NewSecurePass123!",
            },
        )

        self.assertRedirects(response, reverse("login"))
        dashboard_response = existing_client.get(reverse("dashboard"))
        self.assertRedirects(
            dashboard_response,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )


class LoginAbuseProtectionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="login-user",
            email="login@example.com",
            password="CorrectPass123!",
        )

    def tearDown(self):
        cache.clear()

    def test_repeated_invalid_logins_are_rate_limited(self):
        for _ in range(5):
            response = self.client.post(
                reverse("login"),
                {"username": self.user.username, "password": "wrong-password"},
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("login"),
            {"username": self.user.username, "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 429)
