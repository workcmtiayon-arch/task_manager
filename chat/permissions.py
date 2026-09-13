from .models import ConversationMember, Message

def get_active_membership(user, conversation_id):
    """Retourne l'adhésion active de l'utilisateur à une conversation."""
    if user.is_anonymous:
        return None
    return ConversationMember.objects.filter(user=user, conversation_id=conversation_id, left_at__isnull=True).first()

def user_can_access_conversation(user, conversation_id):
    """Indique si l'utilisateur peut accéder au canal WebSocket demandé."""
    return get_active_membership(user, conversation_id) is not None


def get_owned_message(user, message_id, conversation_id):
    """Retourne un message de la conversation uniquement s'il appartient à l'utilisateur."""
    return Message.objects.filter(pk=message_id, conversation_id=conversation_id, sender=user).first()
