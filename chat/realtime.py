"""Routage direct des événements WebSocket pour les conversations individuelles."""

from collections import defaultdict
from threading import Lock


_active_channels = defaultdict(set)
_channels_lock = Lock()


def register_channel(conversation_id, channel_name):
    """Associe un canal WebSocket actif à une conversation individuelle."""
    with _channels_lock:
        _active_channels[str(conversation_id)].add(channel_name)


def unregister_channel(conversation_id, channel_name):
    """Retire un canal WebSocket fermé de la conversation suivie."""
    with _channels_lock:
        channels = _active_channels.get(str(conversation_id), set())
        channels.discard(channel_name)
        if not channels:
            _active_channels.pop(str(conversation_id), None)


def get_conversation_channels(conversation_id):
    """Retourne une copie des canaux actuellement connectés à la conversation."""
    with _channels_lock:
        return tuple(_active_channels.get(str(conversation_id), set()))


async def send_to_conversation(channel_layer, conversation_id, event):
    """Envoie directement un événement à chaque socket actif de la conversation."""
    for channel_name in get_conversation_channels(conversation_id):
        try:
            await channel_layer.send(channel_name, event)
        except Exception:
            # Un canal peut disparaître entre sa lecture et son envoi.
            unregister_channel(conversation_id, channel_name)
