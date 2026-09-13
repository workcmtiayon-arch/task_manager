"""Petites fonctions partagées par les vues HTTP du chat."""

from ..models import Conversation, Message


def preview_text(message):
    """Transforme un message en aperçu court pour les listes de conversations."""
    if message is None:
        return ""
    if message.is_deleted():
        return "Message supprime"
    if message.message_type == Message.MessageType.ATTACHMENT:
        return "Piece jointe"
    text = message.content or ""
    return text if len(text) <= 60 else text[:60] + "…"


def maybe_accept_conversation(conversation, sender):
    """Accepte automatiquement une invitation lorsque son destinataire répond."""
    if conversation.accepted_at is None and sender.id != conversation.initiated_by_id:
        conversation.accept()


def broadcast_event(conversation, event, ignore_errors=True):
    """Diffuse directement un événement aux sockets de la conversation individuelle."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    from ..realtime import send_to_conversation

    if ignore_errors:
        try:
            async_to_sync(send_to_conversation)(get_channel_layer(), conversation.pk, event)
        except Exception:
            # La persistance HTTP reste prioritaire pour les envois tolérants aux pannes du canal.
            pass
        return
    async_to_sync(send_to_conversation)(get_channel_layer(), conversation.pk, event)
