"""Vues HTTP de lecture, d'envoi et de départ des conversations."""

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods

from ..models import Conversation, ConversationMember, Message, MessageAttachment, MessageReceipt
from ..utils import serialize_message
from .common import broadcast_event, maybe_accept_conversation


@login_required
def conversation_messages_json(request, pk):
    """Retourne une page de messages sérialisés, éventuellement antérieure à un identifiant."""
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.is_member(request.user):
        return HttpResponseForbidden("Vous n'etes pas membre de cette conversation.")
    try:
        limit = min(max(int(request.GET.get("limit", 50)), 1), 100)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "La limite doit être un nombre entier."}, status=400)
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
        return HttpResponseForbidden("Vous n'êtes pas membre de cette conversation.")
    content = (request.POST.get("content") or "").strip()
    if not content:
        return JsonResponse({"detail": "Le message ne peut pas être vide."}, status=400)
    if len(content) > 4000:
        return JsonResponse({"detail": "Message trop long (4000 caractères maximum)."}, status=400)
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
        return HttpResponseForbidden("Vous n'êtes pas membre de cette conversation.")
    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        return HttpResponseBadRequest("Aucun fichier recu...")
    if uploaded_file.content_type not in MessageAttachment.ALLOWED_CONTENT_TYPES:
        return HttpResponseBadRequest("Type de fichier non autorisé (images, PDF ou TXT uniquement).")
    if uploaded_file.size > MessageAttachment.MAX_FILE_SIZE:
        return HttpResponseBadRequest("Fichier trop volumineux (10 Mo maximum).")
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
        return HttpResponseForbidden("You are not member of this conversation")
    membership.leave()
    return redirect("chat:conversation_list")
