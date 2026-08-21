from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from config.asgi import application
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




class ChatConsumerTests(TransactionTestCase):
    def setUp(self):
        self.malik = User.objects.create_user(username="malik", email="maliktiayon95@gmail.com", password="pass1234")
        self.honore = User.objects.create_user(username="honore", email="honoretiayon@gmail.com", password="pass1234")
        self.americanboy = User.objects.create_user(username="americanboy", email="etudesamerican@gmail.com", password="pass1234")
        self.conversation = Conversation.objects.get_or_create_private(self.malik, self.honore)

    async def _connect(self, user):
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.conversation.pk}/")
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
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