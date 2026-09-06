from django.test import TestCase
from django.urls import reverse
from django.core import mail
from django.test import override_settings

from chat.models import Conversation, ConversationMember
from projects.models import Project
from tasks.models import Task

from .models import User


class DashboardAndAdministrationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com", password="password123",
            role=User.Role.ADMIN,
        )
        self.member = User.objects.create_user(
            username="member", email="member@example.com", password="password123",
        )
        self.other_member = User.objects.create_user(
            username="other", email="other@example.com", password="password123",
        )

        project = Project.objects.create(user=self.member, name="Projet membre")
        Task.objects.create(project=project, title="Terminée", status=Task.Status.DONE)
        Task.objects.create(project=project, title="À faire", status=Task.Status.TODO)

        conversation = Conversation.objects.create()
        ConversationMember.objects.create(conversation=conversation, user=self.member)
        ConversationMember.objects.create(conversation=conversation, user=self.other_member)

    def test_member_dashboard_shows_only_personal_metrics(self):
        self.client.force_login(self.member)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_dashboard_admin"])
        self.assertEqual(response.context["project_count"], 1)
        self.assertEqual(response.context["task_count"], 2)
        self.assertEqual(response.context["conversation_count"], 1)
        self.assertEqual(response.context["completed_percentage"], 50)
        self.assertEqual(response.context["completed_project_percentage"], 0)
        self.assertNotContains(response, 'href="/accounts/utilisateurs/"')

    def test_admin_dashboard_shows_global_metrics_and_admin_navigation(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_dashboard_admin"])
        self.assertEqual(response.context["user_count"], 3)
        self.assertEqual(response.context["project_count"], 1)
        self.assertEqual(response.context["conversation_count"], 1)
        self.assertContains(response, 'href="/accounts/utilisateurs/"')

    def test_only_admin_can_manage_accounts_and_toggle_status(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse("user_list")).status_code, 403)

        self.client.force_login(self.admin)
        response = self.client.post(reverse("toggle_user_status", args=[self.member.pk]))
        self.assertRedirects(response, reverse("user_list"))
        self.member.refresh_from_db()
        self.assertFalse(self.member.is_active)

    def test_profile_can_be_updated_by_the_owner(self):
        self.client.force_login(self.member)
        response = self.client.post(reverse("profile"), {
            "username": "member",
            "first_name": "Amina",
            "last_name": "Njoya",
            "email": "amina@example.com",
        })

        self.assertRedirects(response, reverse("profile"))
        self.member.refresh_from_db()
        self.assertEqual(self.member.first_name, "Amina")
        self.assertEqual(self.member.email, "amina@example.com")


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="auth-user", email="auth@example.com", password="SecurePass123!",
        )

    def test_verified_reset_flow_renders_new_password_form(self):
        session = self.client.session
        session["reset_verified_user_id"] = self.user.pk
        session.save()

        response = self.client.get(reverse("reset-password"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="new_password1"')
        self.assertContains(response, 'autocomplete="new-password"')

    def test_valid_login_redirects_to_dashboard(self):
        response = self.client.post(reverse("login"), {
            "username": self.user.username,
            "password": "SecurePass123!",
        })

        self.assertRedirects(response, reverse("dashboard"))

    def test_login_form_can_be_submitted_with_csrf_protection_enabled(self):
        csrf_client = self.client_class(enforce_csrf_checks=True)
        response = csrf_client.get(reverse("login"))
        csrf_token = csrf_client.cookies["csrftoken"].value

        response = csrf_client.post(reverse("login"), {
            "username": self.user.username,
            "password": "SecurePass123!",
            "csrfmiddlewaretoken": csrf_token,
        })

        self.assertRedirects(response, reverse("dashboard"))
        self.assertIn("no-cache", response.headers.get("Cache-Control", ""))

    def test_invalid_login_returns_form_errors(self):
        response = self.client.post(reverse("login"), {
            "username": self.user.username,
            "password": "wrong-password",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AuthenticationEmailTests(TestCase):
    def test_otp_email_contains_html_and_plain_text_alternatives(self):
        user = User.objects.create_user(
            username="mail-user", email="mail@example.com", password="SecurePass123!",
        )
        from .tasks import send_otp_email_task

        send_otp_email_task.run(user.pk, "123456", "PASSWORD_RESET")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertIn("123456", mail.outbox[0].alternatives[0][0])
