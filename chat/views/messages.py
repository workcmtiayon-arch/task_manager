"""Vues HTTP de lecture, d'envoi et de départ des conversations."""

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _

from ..models import Conversation, ConversationMember, Message, MessageAttachment, MessageReceipt
from ..utils import serialize_message
from .common import broadcast_event, maybe_accept_conversation


@login_required
def conversation_messages_json(request, pk):
    """Retourne une page de messages sérialisés, éventuellement antérieure à un identifiant."""
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.is_member(request.user):
        return HttpResponseForbidden(_("You are not a member of this conversation."))
    try:
        limit = min(max(int(request.GET.get("limit", 50)), 1), 100)
    except (TypeError, ValueError):
        return JsonResponse({"detail": _("The limit must be an integer.")}, status=400)
    queryset = conversation.messages.select_related("sender").prefetch_related("attachments", "reactions", "receipts")
    before_id = request.GET.get("before")
    if before_id:
        queryset = queryset.filter(pk__lt=before_id)
    messages = list(queryset.order_by("-pk")[:limit])
    messages.reverse()
    return JsonResponse({"messages": [serialize_message(message) for message in messages]})


@login_required
@require_http_methods(["POST"])
def conversation_message_send(request, pk):
    """Enregistre un message texte, même si le WebSocket est indisponible."""
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.is_member(request.user):
        return HttpResponseForbidden(_("You are not a member of this conversation."))
    content = (request.POST.get("content") or "").strip()
    if not content:
        return JsonResponse({"detail": _("The message cannot be empty.")}, status=400)
    if len(content) > 4000:
        return JsonResponse({"detail": _("Message too long (4000 characters maximum).")}, status=400)
    with transaction.atomic():
        message = Message.objects.create(conversation=conversation, sender=request.user, content=content, message_type=Message.MessageType.TEXT)
        other_members = conversation.get_members().exclude(pk=request.user.pk)
        MessageReceipt.objects.bulk_create([MessageReceipt(message=message, user=member) for member in other_members])
        maybe_accept_conversation(conversation, request.user)
        conversation.touch()
    payload = serialize_message(message)
    broadcast_event(conversation, {"type": "chat.message", "message": payload})
    return JsonResponse(payload, status=201)


@login_required
@require_http_methods(["POST"])
def conversation_attachment_upload(request, pk):
    """Enregistre une pièce jointe validée et la diffuse dans la conversation."""
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.is_member(request.user):
        return HttpResponseForbidden(_("You are not a member of this conversation."))
    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        return HttpResponseBadRequest(_("No file received."))
    if uploaded_file.content_type not in MessageAttachment.ALLOWED_CONTENT_TYPES:
        return HttpResponseBadRequest(_("File type not allowed (images, PDF or TXT only)."))
    if uploaded_file.size > MessageAttachment.MAX_FILE_SIZE:
        return HttpResponseBadRequest(_("File too large (10 MB maximum)."))
    with transaction.atomic():
        message = Message.objects.create(conversation=conversation, sender=request.user, content="", message_type=Message.MessageType.ATTACHMENT)
        MessageAttachment.objects.create(message=message, file=uploaded_file, file_name=uploaded_file.name, file_size=uploaded_file.size, content_type=uploaded_file.content_type)
        other_members = conversation.get_members().exclude(pk=request.user.pk)
        MessageReceipt.objects.bulk_create([MessageReceipt(message=message, user=member) for member in other_members])
        maybe_accept_conversation(conversation, request.user)
        conversation.touch()
    payload = serialize_message(message)
    broadcast_event(conversation, {"type": "chat.message", "message": payload}, ignore_errors=False)
    return JsonResponse(payload, status=201)


@login_required
@require_http_methods(["POST"])
def conversation_leave(request, pk):
    """Clôture l'adhésion de l'utilisateur et le redirige vers son inbox."""
    conversation = get_object_or_404(Conversation, pk=pk)
    membership = ConversationMember.objects.filter(conversation=conversation, user=request.user).first()
    if membership is None:
        return HttpResponseForbidden(_("You are not a member of this conversation."))
    membership.leave()
    return redirect("chat:conversation_list")
