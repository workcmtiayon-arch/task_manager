from django.test import TestCase
from django.urls import reverse

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
