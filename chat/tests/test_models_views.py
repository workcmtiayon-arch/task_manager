"""Tests des modèles et endpoints HTTP du chat."""

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings

from ..models import Conversation, Message, MessageReaction

User = get_user_model()


class ConversationModelTests(TransactionTestCase):
    """Vérifie les règles de persistance des conversations et messages."""

    def setUp(self):
        """Crée deux utilisateurs communs aux tests de modèles."""
        self.malik = User.objects.create_user(username="malik", email="maliktiayon95@gmail.com", password="pass1234")
        self.honore = User.objects.create_user(username="honore", email="honoretiayon@gmail.com", password="pass1234")

    def test_get_or_create_private_creates_conversation_with_two_members(self):
        """Vérifie qu'une nouvelle conversation contient ses deux membres actifs."""
        conversation = Conversation.objects.get_or_create_private(self.malik, self.honore)
        self.assertEqual(conversation.memberships.count(), 2)
        self.assertTrue(conversation.is_member(self.malik))
        self.assertTrue(conversation.is_member(self.honore))

    def test_get_or_create_private_is_idempotent(self):
        """Vérifie que l'ordre des utilisateurs ne crée pas un doublon."""
        first = Conversation.objects.get_or_create_private(self.malik, self.honore)
        second = Conversation.objects.get_or_create_private(self.honore, self.malik)
        self.assertEqual(first.pk, second.pk)

    def test_message_delete_is_soft(self):
        """Vérifie qu'une suppression vide le message sans supprimer sa ligne."""
        conversation = Conversation.objects.get_or_create_private(self.malik, self.honore)
        message = Message.objects.create(conversation=conversation, sender=self.malik, content="Salut")
        message.delete()
        self.assertTrue(Message.objects.filter(pk=message.pk).exists())
        message.refresh_from_db()
        self.assertTrue(message.is_deleted())
        self.assertEqual(message.content, "")

    def test_reaction_is_unique_per_user_and_message(self):
        """Vérifie la contrainte d'unicité des réactions."""
        conversation = Conversation.objects.get_or_create_private(self.malik, self.honore)
        message = Message.objects.create(conversation=conversation, sender=self.malik, content="Salut")
        MessageReaction.objects.create(message=message, user=self.honore, reaction=MessageReaction.Reaction.LIKE)
        with self.assertRaises(Exception):
            MessageReaction.objects.create(message=message, user=self.honore, reaction=MessageReaction.Reaction.LOVE)


class UserSearchViewTests(TestCase):
    """Vérifie la recherche utilisateur et sa réponse JSON."""

    def setUp(self):
        """Crée l'utilisateur courant et un résultat disponible."""
        self.current_user = User.objects.create_user(username="amina", email="amina@example.com", password="pass1234")
        self.available_user = User.objects.create_user(username="malik", email="malik@example.com", password="pass1234")

    def test_opening_search_displays_the_search_interface(self):
        """Vérifie que l'accès navigateur rend le template de recherche."""
        self.client.force_login(self.current_user)
        response = self.client.get("/chat/users/search/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chat/user_search.html")

    def test_ajax_search_returns_available_users(self):
        """Vérifie que l'appel AJAX retourne les utilisateurs filtrés."""
        self.client.force_login(self.current_user)
        response = self.client.get("/chat/users/search/", {"q": "mal"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["users"], [{"id": self.available_user.id, "username": "malik"}])


class ConversationDetailTemplateTests(TestCase):
    """Vérifie les données essentielles injectées dans le détail."""

    def test_conversation_detail_uses_the_registered_login_url(self):
        """Vérifie que le template utilise l'URL de connexion enregistrée."""
        user = User.objects.create_user(username="amina", email="amina@example.com", password="pass1234")
        other_user = User.objects.create_user(username="malik", email="malik@example.com", password="pass1234")
        conversation = Conversation.objects.create(initiated_by=user)
        conversation.add_member(user)
        conversation.add_member(other_user)
        self.client.force_login(user)
        response = self.client.get(f"/chat/{conversation.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-login-url="/accounts/login/"')


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class MessageSendingTests(TestCase):
    """Vérifie les endpoints d'envoi et de réaction avec le channel layer mémoire."""

    def test_first_message_is_persisted_and_creates_an_invitation_for_the_recipient(self):
        """Vérifie qu'un premier message crée l'invitation du destinataire."""
        sender = User.objects.create_user(username="amina", email="amina@example.com", password="pass1234")
        recipient = User.objects.create_user(username="malik", email="malik@example.com", password="pass1234")
        conversation = Conversation.objects.get_or_create_private(sender, recipient)
        self.client.force_login(sender)
        response = self.client.post(f"/chat/{conversation.pk}/messages/send/", {"content": "Bonjour Malik"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Message.objects.filter(conversation=conversation, content="Bonjour Malik").exists())
        self.assertEqual(Conversation.objects.invitations_for_user(recipient).count(), 1)

    def test_reaction_http_fallback_sets_and_removes_reaction(self):
        """Vérifie le fallback HTTP de création puis suppression d'une réaction."""
        current_user = User.objects.create_user(username="amina", email="amina@example.com", password="pass1234")
        recipient = User.objects.create_user(username="malik", email="malik@example.com", password="pass1234")
        conversation = Conversation.objects.get_or_create_private(current_user, recipient)
        message = Message.objects.create(conversation=conversation, sender=recipient, content="React to this")
        self.client.force_login(current_user)
        response = self.client.post(f"/chat/{conversation.pk}/reactions/set/", {"message_id": message.pk, "reaction": MessageReaction.Reaction.LOVE})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MessageReaction.objects.get(message=message, user=current_user).reaction, "LOVE")
        response = self.client.post(f"/chat/{conversation.pk}/reactions/remove/", {"message_id": message.pk})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MessageReaction.objects.filter(message=message, user=current_user).exists())

    def test_reaction_endpoint_rejects_invalid_value(self):
        """Vérifie le rejet d'une valeur de réaction inconnue."""
        current_user = User.objects.create_user(username="amina", email="amina@example.com", password="pass1234")
        recipient = User.objects.create_user(username="malik", email="malik@example.com", password="pass1234")
        conversation = Conversation.objects.get_or_create_private(current_user, recipient)
        message = Message.objects.create(conversation=conversation, sender=recipient, content="React to this")
        self.client.force_login(current_user)
        response = self.client.post(f"/chat/{conversation.pk}/reactions/set/", {"message_id": message.pk, "reaction": "INVALID"})
        self.assertEqual(response.status_code, 400)

    def test_reaction_endpoint_rejects_non_members(self):
        """Vérifie qu'un utilisateur externe ne peut pas réagir."""
        owner = User.objects.create_user(username="owner", email="owner@example.com", password="pass1234")
        recipient = User.objects.create_user(username="recipient", email="recipient@example.com", password="pass1234")
        outsider = User.objects.create_user(username="outsider", email="outsider@example.com", password="pass1234")
        conversation = Conversation.objects.get_or_create_private(owner, recipient)
        message = Message.objects.create(conversation=conversation, sender=owner, content="Private")
        self.client.force_login(outsider)
        response = self.client.post(f"/chat/{conversation.pk}/reactions/set/", {"message_id": message.pk, "reaction": MessageReaction.Reaction.LIKE})
        self.assertEqual(response.status_code, 403)
