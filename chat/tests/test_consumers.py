"""Tests du protocole WebSocket du chat."""

import importlib

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings

from ..models import Conversation, Message

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatConsumerTests(TransactionTestCase):
    """Vérifie les connexions, diffusions et permissions du consumer."""

    def setUp(self):
        """Crée les utilisateurs et la conversation de test WebSocket."""
        self.malik = User.objects.create_user(username="malik", email="maliktiayon95@gmail.com", password="pass1234")
        self.honore = User.objects.create_user(username="honore", email="honoretiayon@gmail.com", password="pass1234")
        self.americanboy = User.objects.create_user(username="americanboy", email="etudesamerican@gmail.com", password="pass1234")
        self.conversation = Conversation.objects.get_or_create_private(self.malik, self.honore)

    async def _connect(self, user):
        """Ouvre un communicator authentifié sur la conversation de test."""
        import config.asgi
        application = importlib.reload(config.asgi).application
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.conversation.pk}/")
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        if connected:
            await communicator.receive_json_from()
        return communicator, connected

    async def test_member_can_connect(self):
        """Vérifie qu'un membre actif peut établir la connexion."""
        communicator, connected = await self._connect(self.malik)
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_non_member_is_rejected(self):
        """Vérifie qu'un utilisateur extérieur est refusé."""
        communicator, connected = await self._connect(self.americanboy)
        self.assertFalse(connected)

    async def test_send_message_is_persisted_and_broadcast(self):
        """Vérifie qu'un message est persisté et reçu par l'autre socket."""
        malik_comm, _ = await self._connect(self.malik)
        honore_comm, _ = await self._connect(self.honore)
        await malik_comm.send_json_to({"type": "message.send", "content": "Salut honore"})
        response = await honore_comm.receive_json_from()
        self.assertEqual(response["type"], "message.new")
        self.assertEqual(response["content"], "Salut honore")
        count = await database_sync_to_async(Message.objects.filter(conversation=self.conversation).count)()
        self.assertEqual(count, 1)
        await malik_comm.disconnect()
        await honore_comm.disconnect()

    async def test_only_author_can_edit_message(self):
        """Vérifie que seul l'auteur peut modifier un message."""
        malik_comm, _ = await self._connect(self.malik)
        honore_comm, _ = await self._connect(self.honore)
        await malik_comm.send_json_to({"type": "message.send", "content": "Premier jet"})
        await honore_comm.receive_json_from()
        message_id = await database_sync_to_async(lambda: Message.objects.filter(conversation=self.conversation).first().id)()
        await honore_comm.send_json_to({"type": "message.edit", "message_id": message_id, "content": "piraté"})
        error_response = await honore_comm.receive_json_from()
        self.assertEqual(error_response["type"], "error")
        await malik_comm.disconnect()
        await honore_comm.disconnect()
