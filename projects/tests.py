from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Project


class ProjectListDisplayTests(TestCase):
    def test_project_list_uses_the_project_overview(self):
        user = User.objects.create_user(
            username="nadia", email="nadia@example.com", password="password123",
        )
        Project.objects.create(user=user, name="Plateforme web")

        self.client.force_login(user)
        response = self.client.get(reverse("project_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Donnez vie à vos idées, projet par projet.")
        self.assertContains(response, "Plateforme web")
        self.assertEqual(response.context["active_nav"], "projects")
