from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from . import permissions as chat_permissions
from .models import Conversation, Message, MessageReaction, MessageReceipt
from .utils import serialize_message


class ChatConsumer(AsyncJsonWebsocketConsumer):
    
    # Cycle de vie de la connexion
    
    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"conversation_{self.conversation_id}"
        
        if self.user.is_anonymous:
            await self.close(code=4001) # non authentifié
            return

        is_member = await database_sync_to_async(chat_permissions.user_can_access_conversation)(
            self.user, self.conversation_id,
        )

        if not is_member:
            await self.close(code=4003) # accès refusé
            return
    
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Rattrapage : les messages reçus pendant l'absence passent à "livré"
        delivered_ids = await database_sync_to_async(self._mark_pending_as_delivered)()
        if delivered_ids:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat.receipt_update",
                    "message_ids": delivered_ids,
                    "user_id": self.user.id,
                    "status": "delivered",
                },
            )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            
            
    