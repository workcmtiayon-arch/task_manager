from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from .models import Conversation, Message, MessageReaction

# Create your tests here.

User = get_user_model()



class ConversationModelTests(TransactionTestCase):
    def setUp(self):
        self.malik = User.objects.create_user(username="malik", email="maliktiayon95@gmail.com", password="pass1234")
        self.honore = User.objects.create_user(username="honore", email="honoretiayon@gmail.com", password="pass1234")


    def test_get_or_create_private_creates_conversation_with_two_members(self):
        conversation = Conversation.objects.get_or_create_private(self.malik, self.honore)
        self.assertEqual(conversation.memberships.count(), 2)
        self.assertTrue(conversation.is_member(self.malik))
        self.assertTrue(conversation.is_member(self.honore))


    def test_get_or_create_private_is_idempotent(self):
        first = Conversation.objects.get_or_create_private(self.malik, self.honore)
        second = Conversation.objects.get_or_create_private(self.honore, self.malik)
        self.assertEqual(first.pk, second.pk)


    def test_message_delete_is_soft(self):
        conversation = Conversation.objects.get_or_create_private(self.malik, self.honore)
        message = Message.objects.create(conversation=conversation, sender=self.malik, content="Salut")
        message.delete()
        self.assertTrue(Message.objects.filter(pk=message.pk).exists())
        message.refresh_from_db()
        self.assertTrue(message.is_deleted())
        self.assertEqual(message.content, "")


    def test_reaction_is_unique_per_user_and_message(self):
        conversation = Conversation.objects.get_or_create_private(self.malik, self.honore)
        message = Message.objects.create(conversation=conversation, sender=self.malik, content="Salut")
        MessageReaction.objects.create(message=message, user=self.honore, reaction=MessageReaction.Reaction.LIKE)
        with self.assertRaises(Exception):
            MessageReaction.objects.create(message=message, user=self.honore, reaction=MessageReaction.Reaction.LOVE)


class UserSearchViewTests(TestCase):
    def setUp(self):
        self.current_user = User.objects.create_user(
            username="amina", email="amina@example.com", password="pass1234",
        )
        self.available_user = User.objects.create_user(
            username="malik", email="malik@example.com", password="pass1234",
        )

    def test_opening_search_displays_the_search_interface(self):
        self.client.force_login(self.current_user)

        response = self.client.get("/chat/users/search/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "chat/user_search.html")

    def test_ajax_search_returns_available_users(self): 
        self.client.force_login(self.current_user)

        response = self.client.get(
            "/chat/users/search/", {"q": "mal"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["users"], [{"id": self.available_user.id, "username": "malik"}])


class ConversationDetailTemplateTests(TestCase):
    def test_conversation_detail_uses_the_registered_login_url(self):
        user = User.objects.create_user(
            username="amina", email="amina@example.com", password="pass1234",
        )
        other_user = User.objects.create_user(
            username="malik", email="malik@example.com", password="pass1234",
        )
        conversation = Conversation.objects.create(initiated_by=user)
        conversation.add_member(user)
        conversation.add_member(other_user)

        self.client.force_login(user)
        response = self.client.get(f"/chat/{conversation.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-login-url="/accounts/login/"')


@override_settings(CHANNEL_LAYERS={
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
})
class MessageSendingTests(TestCase):
    def test_first_message_is_persisted_and_creates_an_invitation_for_the_recipient(self):
        sender = User.objects.create_user(
            username="amina", email="amina@example.com", password="pass1234",
        )
        recipient = User.objects.create_user(
            username="malik", email="malik@example.com", password="pass1234",
        )
        conversation = Conversation.objects.get_or_create_private(sender, recipient)

        self.client.force_login(sender)
        response = self.client.post(
            f"/chat/{conversation.pk}/messages/send/", {"content": "Bonjour Malik"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Message.objects.filter(conversation=conversation, content="Bonjour Malik").exists())
        self.assertEqual(Conversation.objects.invitations_for_user(recipient).count(), 1)

    def test_reaction_http_fallback_sets_and_removes_reaction(self):
        current_user = User.objects.create_user(username="amina", email="amina@example.com", password="pass1234")
        recipient = User.objects.create_user(username="malik", email="malik@example.com", password="pass1234")
        conversation = Conversation.objects.get_or_create_private(current_user, recipient)
        message = Message.objects.create(conversation=conversation, sender=recipient, content="React to this")
        self.client.force_login(current_user)

        response = self.client.post(
            f"/chat/{conversation.pk}/reactions/set/",
            {"message_id": message.pk, "reaction": MessageReaction.Reaction.LOVE},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(MessageReaction.objects.get(message=message, user=current_user).reaction, "LOVE")

        response = self.client.post(
            f"/chat/{conversation.pk}/reactions/remove/", {"message_id": message.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MessageReaction.objects.filter(message=message, user=current_user).exists())




@override_settings(CHANNEL_LAYERS={
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
})
class ChatConsumerTests(TransactionTestCase):
    def setUp(self):
        self.malik = User.objects.create_user(username="malik", email="maliktiayon95@gmail.com", password="pass1234")
        self.honore = User.objects.create_user(username="honore", email="honoretiayon@gmail.com", password="pass1234")
        self.americanboy = User.objects.create_user(username="americanboy", email="etudesamerican@gmail.com", password="pass1234")
        self.conversation = Conversation.objects.get_or_create_private(self.malik, self.honore)

    async def _connect(self, user):
        import importlib
        import config.asgi
        application = importlib.reload(config.asgi).application

        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.conversation.pk}/")
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        if connected:
            await communicator.receive_json_from()
        return communicator, connected
    
    async def test_member_can_connect(self):
        communicator, connected = await self._connect(self.malik)
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_non_member_is_rejected(self):
        communicator, connected = await self._connect(self.americanboy)
        self.assertFalse(connected)

    async def test_send_message_is_persisted_and_broadcast(self):
        malik_comm, _ = await self._connect(self.malik)
        honore_comm, _ = await self._connect(self.honore)
        
        await malik_comm.send_json_to({"type": "message.send", "content": "Salut honore"})
        
        response = await honore_comm.receive_json_from()
        self.assertEqual(response["type"], "message.new")
        self.assertEqual(response["content"], "Salut honore")

        count = await database_sync_to_async(
            Message.objects.filter(conversation=self.conversation).count
        )()
        self.assertEqual(count, 1)

        await malik_comm.disconnect()
        await honore_comm.disconnect()

    async def test_only_author_can_edit_message(self):
        malik_comm, _ = await self._connect(self.malik)
        honore_comm, _ = await self._connect(self.honore)
        
        await malik_comm.send_json_to({"type": "message.send", "content": "Premier jet"})
        await honore_comm.receive_json_from() 
        
        message_id = await database_sync_to_async(
            lambda: Message.objects.filter(conversation=self.conversation).first().id
        )()
        
        await honore_comm.send_json_to({"type": "message.edit", "message_id": message_id, "content": "piraté"})
        error_response = await honore_comm.receive_json_from()
        self.assertEqual(error_response["type"], "error")
        
        await malik_comm.disconnect()
        await honore_comm.disconnect()
