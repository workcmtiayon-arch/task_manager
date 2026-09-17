from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from projects.models import Project
from tasks.models import Task

from .context import build_user_context
from .models import Conversation, Message


class AIContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", email="owner@example.com", password="password123")
        self.other = User.objects.create_user(username="other", email="other@example.com", password="password123")

    def test_context_contains_only_owned_projects(self):
        owned = Project.objects.create(user=self.user, name="Owned")
        Task.objects.create(project=owned, title="Owned task")
        foreign = Project.objects.create(user=self.other, name="Foreign")
        Task.objects.create(project=foreign, title="Private task")
        context = build_user_context(self.user)
        self.assertEqual([item["name"] for item in context], ["Owned"])
        self.assertEqual(context[0]["tasks"][0]["title"], "Owned task")


class AIChatViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="chatuser", email="chat@example.com", password="password123")
        self.client.force_login(self.user)

    def test_chat_requires_post(self):
        self.assertEqual(self.client.get(reverse("ai:chat")).status_code, 405)

    @patch("ai.services.get_provider")
    def test_chat_persists_user_and_assistant_messages(self, get_provider):
        provider = get_provider.return_value
        provider.name = "gemini"
        provider.model = "gemini-2.0-flash"
        provider.complete.return_value = "Voici un résumé."
        response = self.client.post(reverse("ai:chat"), {"content": "Résume mes tâches"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        conversation = Conversation.objects.get(pk=response.json()["conversation_id"])
        self.assertEqual(conversation.user, self.user)
        self.assertEqual(Message.objects.filter(conversation=conversation).count(), 2)

    def test_invalid_json_is_rejected(self):
        response = self.client.post(reverse("ai:chat"), "not-json", content_type="application/json")
        self.assertEqual(response.status_code, 400)
