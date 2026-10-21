from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from projects.models import Project
from tasks.models import Task

from .context import build_user_context
from .models import Conversation, Message
from .exceptions import AIProviderError
from .providers import GeminiProvider, OpenAIProvider


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
        cache.clear()
        self.user = User.objects.create_user(username="chatuser", email="chat@example.com", password="password123")
        self.client.force_login(self.user)

    def tearDown(self):
        cache.clear()

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

    @override_settings(AI_MAX_REQUEST_BYTES=32)
    @patch("ai.services.get_provider")
    def test_oversized_request_is_rejected_before_provider_call(self, get_provider):
        response = self.client.post(
            reverse("ai:chat"),
            '{"content":"' + ("x" * 64) + '"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 413)
        get_provider.assert_not_called()

    def test_non_object_json_is_rejected(self):
        response = self.client.post(reverse("ai:chat"), "[]", content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_project_identifier_is_rejected_as_bad_request(self):
        response = self.client.post(
            reverse("ai:chat"),
            {"content": "Summarize", "project_id": []},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(AI_RATE_LIMIT_ATTEMPTS=1)
    @patch("ai.services.get_provider")
    def test_ai_requests_are_rate_limited_per_user_and_address(self, get_provider):
        provider = get_provider.return_value
        provider.name = "gemini"
        provider.model = "gemini-2.0-flash"
        provider.complete.return_value = "Done"
        url = reverse("ai:chat")
        payload = {"content": "First request"}
        self.assertEqual(self.client.post(url, payload, content_type="application/json").status_code, 200)
        response = self.client.post(url, {"content": "Second request"}, content_type="application/json")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(provider.complete.call_count, 1)

    @patch("ai.services.get_provider")
    def test_project_context_must_belong_to_the_request_user(self, get_provider):
        other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="password123",
        )
        foreign_project = Project.objects.create(
            user=other,
            name="Private project",
        )
        response = self.client.post(
            reverse("ai:chat"),
            {"content": "Summarize", "project_id": foreign_project.pk},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        get_provider.assert_not_called()

    @patch("ai.services.get_provider")
    def test_conversation_history_must_belong_to_the_request_user(self, get_provider):
        other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="password123",
        )
        foreign_conversation = Conversation.objects.create(user=other, title="Private history")
        response = self.client.post(
            reverse("ai:chat"),
            {"content": "Continue this conversation", "conversation_id": foreign_conversation.pk},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        get_provider.assert_not_called()

    @patch("ai.services.get_provider")
    def test_failed_provider_call_does_not_leave_an_empty_conversation(self, get_provider):
        get_provider.return_value.complete.side_effect = AIProviderError("Unavailable")
        response = self.client.post(
            reverse("ai:chat"),
            {"content": "Try this"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertFalse(Conversation.objects.exists())

    @override_settings(AI_MAX_CONTEXT_CHARS=100)
    @patch("ai.services.get_provider")
    def test_context_sent_to_provider_stays_within_configured_size(self, get_provider):
        project = Project.objects.create(user=self.user, name="Big project", description="d" * 4000)
        for index in range(10):
            Task.objects.create(project=project, title=f"Task {index}", description="x" * 1000)
        provider = get_provider.return_value
        provider.name = "gemini"
        provider.model = "gemini-2.0-flash"
        provider.complete.return_value = "Done"
        response = self.client.post(
            reverse("ai:chat"),
            {"content": "Summarize"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(provider.complete.call_args.args[0][0]["content"].split(": ", 1)[1]), 100)

    @override_settings(AI_MAX_HISTORY_MESSAGES=2)
    @patch("ai.services.get_provider")
    def test_provider_receives_only_the_latest_conversation_history(self, get_provider):
        conversation = Conversation.objects.create(user=self.user, title="History")
        for index in range(5):
            Message.objects.create(conversation=conversation, role=Message.Role.USER, content=f"old {index}")
        provider = get_provider.return_value
        provider.name = "gemini"
        provider.model = "gemini-2.0-flash"
        provider.complete.return_value = "Done"
        response = self.client.post(
            reverse("ai:chat"),
            {"content": "new", "conversation_id": conversation.pk},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        sent = provider.complete.call_args.args[0]
        self.assertEqual([item["content"] for item in sent[1:-1]], ["old 3", "old 4"])

    @override_settings(AI_MAX_HISTORY_CHARS=5)
    @patch("ai.services.get_provider")
    def test_conversation_history_is_also_bounded_by_total_characters(self, get_provider):
        conversation = Conversation.objects.create(user=self.user, title="History")
        Message.objects.create(conversation=conversation, role=Message.Role.USER, content="old")
        Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content="too long")
        provider = get_provider.return_value
        provider.name = "gemini"
        provider.model = "gemini-2.0-flash"
        provider.complete.return_value = "Done"
        response = self.client.post(
            reverse("ai:chat"),
            {"content": "new", "conversation_id": conversation.pk},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        sent = provider.complete.call_args.args[0]
        self.assertEqual(sent[1:-1], [])

    @patch("ai.services.get_provider")
    def test_oversized_provider_response_is_rejected_before_persistence(self, get_provider):
        get_provider.return_value.complete.return_value = "x" * 12001
        response = self.client.post(
            reverse("ai:chat"),
            {"content": "Try this"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertFalse(Conversation.objects.exists())


class ProviderOutputLimitTests(TestCase):
    @patch("ai.providers.BaseProvider._post")
    def test_openai_request_sets_a_generation_limit(self, post):
        post.return_value = {"choices": [{"message": {"content": "ok"}}]}
        provider = OpenAIProvider("key", "model")
        provider.complete([])
        self.assertEqual(post.call_args.args[1]["max_completion_tokens"], 1024)

    @patch("ai.providers.BaseProvider._post")
    def test_gemini_request_sets_a_generation_limit(self, post):
        post.return_value = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        provider = GeminiProvider("key", "model")
        provider.complete([])
        self.assertEqual(post.call_args.args[1]["generationConfig"]["maxOutputTokens"], 1024)

    @patch("ai.providers.BaseProvider._post")
    def test_gemini_sends_api_key_in_header_not_url(self, post):
        post.return_value = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        GeminiProvider("secret-key", "model").complete([])
        url, _, headers = post.call_args.args
        self.assertNotIn("secret-key", url)
        self.assertEqual(headers["x-goog-api-key"], "secret-key")

    @patch("ai.providers.BaseProvider._post")
    def test_gemini_sends_system_context_separately_from_chat_turns(self, post):
        post.return_value = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        GeminiProvider("key", "model").complete([
            {"role": "system", "content": "Use only this user's task data."},
            {"role": "user", "content": "Summarize"},
            {"role": "assistant", "content": "Earlier answer"},
        ])
        payload = post.call_args.args[1]
        self.assertEqual(
            payload["system_instruction"]["parts"][0]["text"],
            "Use only this user's task data.",
        )
        self.assertEqual([turn["role"] for turn in payload["contents"]], ["user", "model"])
