"""Diffusion des événements vers tous les sockets d'une conversation."""


def conversation_group_name(conversation_id):
    """Construit un nom de groupe Channels stable entre processus web."""
    return f"chat_conversation_{conversation_id}"


async def send_to_conversation(channel_layer, conversation_id, event):
    """Diffuse un événement par le channel layer partagé, y compris entre workers."""
    await channel_layer.group_send(conversation_group_name(conversation_id), event)
