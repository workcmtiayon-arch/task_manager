from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from projects.models import Project

from .models import Task


class TaskListDisplayTests(TestCase):
    def test_sidebar_task_page_uses_the_new_task_overview(self):
        user = User.objects.create_user(
            username="amina", email="amina@example.com", password="password123",
        )
        project = Project.objects.create(user=user, name="Site vitrine")
        Task.objects.create(project=project, title="Préparer les maquettes", status=Task.Status.IN_PROGRESS)

        self.client.force_login(user)
        response = self.client.get(reverse("task_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gardez le cap sur vos priorités.")
        self.assertContains(response, "Préparer les maquettes")
        self.assertContains(response, 'nav-link--active')
        self.assertEqual(response.context["active_nav"], "tasks")
