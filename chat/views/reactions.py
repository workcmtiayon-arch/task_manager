"""Vues HTTP de secours pour poser et retirer une réaction."""

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _

from ..models import Conversation, Message, MessageReaction
from ..utils import serialize_reactions
from .common import broadcast_event


def reaction_message(request, pk, remove=False):
    """Applique ou supprime la réaction de l'utilisateur sur un message autorisé."""
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.is_member(request.user):
        return HttpResponseForbidden(_("You are not a member of this conversation."))
    message = get_object_or_404(Message, pk=request.POST.get("message_id"), conversation=conversation)
    if remove:
        MessageReaction.objects.filter(message=message, user=request.user).delete()
    else:
        reaction_value = request.POST.get("reaction")
        valid_values = [choice[0] for choice in MessageReaction.Reaction.choices]
        if reaction_value not in valid_values:
            return JsonResponse({"detail": _("Invalid reaction.")}, status=400)
        reaction, created = MessageReaction.objects.get_or_create(message=message, user=request.user, defaults={"reaction": reaction_value})
        if not created:
            reaction.change(reaction_value)
    reactions = serialize_reactions(message)
    broadcast_event(conversation, {"type": "chat.reaction_update", "message_id": message.pk, "reactions": reactions})
    return JsonResponse({"message_id": message.pk, "reactions": reactions})


@login_required
@require_http_methods(["POST"])
def conversation_reaction_set(request, pk):
    """Traite la réaction choisie par l'utilisateur via HTTP."""
    return reaction_message(request, pk)


@login_required
@require_http_methods(["POST"])
def conversation_reaction_remove(request, pk):
    """Retire la réaction de l'utilisateur via HTTP."""
    return reaction_message(request, pk, remove=True)
