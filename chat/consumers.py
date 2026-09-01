from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from . import permissions as chat_permissions

from .models import Conversation, Message, MessageReaction, MessageReceipt
from .utils import serialize_message


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"conversation_{self.conversation_id}"

        if self.user.is_anonymous:
            await self.close(code=4001)  # non authentifié
            return

        is_member = await database_sync_to_async(chat_permissions.user_can_access_conversation)(
            self.user, self.conversation_id,
        )
        if not is_member:
            await self.close(code=4003)  # accès refusé
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "connection.ready", "conversation_id": int(self.conversation_id)})

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
            
    
    async def receive_json(self, content, **kwargs):
        event_type = content.get("type")
        try:
            if event_type == "message.send":
                await self.handle_message_send(content)
            elif event_type == "message.edit":
                await self.handle_message_edit(content)
            elif event_type == "message.delete":
                await self.handle_message_delete(content)
            elif event_type == "message.read":
                await self.handle_message_read(content)
            elif event_type == "reaction.set":
                await self.handle_reaction_set(content)
            elif event_type == "reaction.remove":
                await self.handle_reaction_remove(content)
            elif event_type in {"typing.start", "typing.stop"}:
                await self.handle_typing(event_type == "typing.start")
            else:
                await self.send_json({"type": "error", "detail": f"Type d'évènement inconnu : {event_type}"})
        except ValueError as exc:
            await self.send_json({"type": "error", "detail": str(exc)})
        except PermissionError:
            await self.send_json({"type": "error", "detail": "Action non autorisée."})
        except (Conversation.DoesNotExist, Message.DoesNotExist):
            await self.send_json({"type": "error", "detail": "La ressource demandée est introuvable."})


    async def handle_message_send(self, content):
        text = (content.get("content") or "").strip()
        if not text:
            raise ValueError("Le message ne peut pas être vide.")
        if len(text) > 4000:
            raise ValueError("Message trop long (4000 caractères maximum).")

        message_data = await database_sync_to_async(self._create_text_message)(text)
        await self.channel_layer.group_send(
            self.group_name, {"type": "chat.message", "message": message_data},
        )

    async def handle_message_edit(self, content):
        message_id = content.get("message_id")
        new_text = (content.get("content") or "").strip()
        if not message_id or not new_text:
            raise ValueError("message_id et content sont requis.")

        message_data = await database_sync_to_async(self._edit_message)(message_id, new_text)
        await self.channel_layer.group_send(
            self.group_name, {"type": "chat.message_edited", "message": message_data},
        )

    async def handle_message_delete(self, content):
        message_id = content.get("message_id")
        if not message_id:
            raise ValueError("message_id est requis.")

        message_data = await database_sync_to_async(self._delete_message)(message_id)
        await self.channel_layer.group_send(
            self.group_name, {"type": "chat.message_deleted", "message": message_data},
        )

    async def handle_message_read(self, content):
        message_id = content.get("message_id")
        if not message_id:
            raise ValueError("message_id est requis.")

        updated = await database_sync_to_async(self._mark_message_read)(message_id)
        if updated:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat.receipt_update",
                    "message_ids": [message_id],
                    "user_id": self.user.id,
                    "status": "read",
                },
            )


    async def handle_reaction_set(self, content):
        message_id = content.get("message_id")
        reaction_value = content.get("reaction")
        valid_values = [choice[0] for choice in MessageReaction.Reaction.choices]
        if not message_id or reaction_value not in valid_values:
            raise ValueError("message_id et une reaction valide sont requis.")

        summary = await database_sync_to_async(self._set_reaction)(message_id, reaction_value)
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "chat.reaction_update", "message_id": message_id, "reactions": summary},
        )

    async def handle_reaction_remove(self, content):
        message_id = content.get("message_id")
        if not message_id:
            raise ValueError("message_id est requis.")

        summary = await database_sync_to_async(self._remove_reaction)(message_id)
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "chat.reaction_update", "message_id": message_id, "reactions": summary},
        )

    async def handle_typing(self, is_typing):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat.typing_update",
                "user_id": self.user.id,
                "username": self.user.username,
                "is_typing": is_typing,
            },
        )


    async def chat_message(self, event):
        await self.send_json({**event["message"], "type": "message.new"})

    async def chat_message_edited(self, event):
        await self.send_json({**event["message"], "type": "message.edited"})

    async def chat_message_deleted(self, event):
        await self.send_json({**event["message"], "type": "message.deleted"})

    async def chat_receipt_update(self, event):
        await self.send_json({
            "type": "receipt.update",
            "message_ids": event["message_ids"],
            "user_id": event["user_id"],
            "status": event["status"],
        })

    async def chat_reaction_update(self, event):
        await self.send_json({
            "type": "reaction.update",
            "message_id": event["message_id"],
            "reactions": event["reactions"],
        })

    async def chat_typing_update(self, event):
        if event["user_id"] != self.user.id:
            await self.send_json({
                "type": "typing.update",
                "user_id": event["user_id"],
                "username": event["username"],
                "is_typing": event["is_typing"],
            })


    def _create_text_message(self, text):
        conversation = Conversation.objects.get(pk=self.conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=text,
            message_type=Message.MessageType.TEXT,
        )
        other_members = conversation.get_members().exclude(pk=self.user.pk)
        MessageReceipt.objects.bulk_create([
            MessageReceipt(message=message, user=member) for member in other_members
        ])
        
        if conversation.accepted_at is None and self.user.id != conversation.initiated_by_id:
            conversation.accept()
        conversation.touch()
        return serialize_message(message)

    def _edit_message(self, message_id, new_text):
        message = Message.objects.select_related("sender").get(
            pk=message_id, conversation_id=self.conversation_id,
        )
        if message.sender_id != self.user.id:
            raise PermissionError("Seul l'auteur peut modifier ce message.")
        message.edit(new_text)
        return serialize_message(message)

    def _delete_message(self, message_id):
        message = Message.objects.select_related("sender").get(
            pk=message_id, conversation_id=self.conversation_id,
        )
        if message.sender_id != self.user.id:
            raise PermissionError("Seul l'auteur peut supprimer ce message.")
        message.delete()
        return serialize_message(message)

    def _mark_message_read(self, message_id):
        receipt = MessageReceipt.objects.filter(message_id=message_id, user=self.user).first()
        if receipt is None:
            return False
        receipt.mark_as_read()
        return True

    def _mark_pending_as_delivered(self):
        pending = MessageReceipt.objects.filter(
            message__conversation_id=self.conversation_id,
            user=self.user,
            delivered_at__isnull=True,
        )
        ids = list(pending.values_list("message_id", flat=True))
        for receipt in pending:
            receipt.mark_as_delivered()
        return ids

    def _set_reaction(self, message_id, reaction_value):
        message = Message.objects.get(
            pk=message_id,
            conversation_id=self.conversation_id,
            conversation__memberships__user=self.user,
            conversation__memberships__left_at__isnull=True,
        )
        reaction, created = MessageReaction.objects.get_or_create(
            message=message, user=self.user, defaults={"reaction": reaction_value},
        )
        if not created:
            reaction.change(reaction_value)
        from .utils import serialize_reactions
        return serialize_reactions(message)

    def _remove_reaction(self, message_id):
        message = Message.objects.get(
            pk=message_id,
            conversation_id=self.conversation_id,
            conversation__memberships__user=self.user,
            conversation__memberships__left_at__isnull=True,
        )
        MessageReaction.objects.filter(message=message, user=self.user).delete()
        from .utils import serialize_reactions
        return serialize_reactions(message)
