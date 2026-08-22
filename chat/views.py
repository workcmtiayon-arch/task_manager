from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction

from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Conversation, ConversationMember, Message, MessageAttachment, MessageReceipt
from .utils import serialize_message

# Create your views here.

User = get_user_model()




def _preview_text(message):
    if message is None:
        return ""
    if message.is_deleted():
        return "Message supprime"
    if message.message_type == Message.MessageType.ATTACHMENT:
        return "Piece jointe"
    text = message.content or ""
    return text if len(text) <= 60 else text[:60] + "…"
    
    
def _maybe_accept_conversation(conversation, sender):
    if conversation.accepted_at is None and sender.id != conversation.initialed_by_id:
        conversation.accept()
        

@login_required
def conversation_list(request):
    conversations = Conversation.objects.for_user_inbox(request.user).order_by("-updated_at")
    items = []
    for conversation in conversations:
        other_user = conversation.get_members().exclude(pk=request.user.pk).first()
        items.append({
            "conversation": conversation,
            "other_user": other_user,
            "preview": _preview_text(conversation.get_last_message()),
        })
    
    invitations_count = Conversation.objects.invitations_for_user(request.user).count()
    return render(request, "chat/conversation_list.html", {
        "items" : items,
        "invitations_count": invitations_count,
    })


@login_required
def user_search(request):
    query = (request.GET.get("q") or "").strip()
    users = []
    if query:
        users = list(
            User.objects.filter(username_icontains=query)
            .exclude(pk=request.user.pk)
            .order_by("username")[:20]
        )
    return JsonResponse({"users": [{"id": u.id, "username": u.username} for u in users]})


@login_required
def conversation_start(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target.pk == request.user.pk:
        return HttpResponseBadRequest("Impossible de démarrer une conversation avec soi-même.")
    conversation = Conversation.objects.get_or_create_private(request.user, target)
    return redirect("chat:conversation_detail", pk=conversation.pk)


@login_required
def conversation_detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.is_member(request.user):
        return HttpResponseForbidden("Vous n'etes pas membre de cette conversation.")
    other_user = conversation.get_members().exclude(pk=request.user.pk).first()
    return render(request, "chat/conversation_detail.html", {
        "conversation": conversation,
        "other_user": other_user,
        "is_invitation": conversation.is_invitation_for(request.user),
    })


@login_required
def conversation_messages_json(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.is_member(request.user):
        return HttpResponseForbidden("Vous n'etes pas membre de cette conversation.")

    limit = min(int(request.GET.get("limit", 50)), 100)
    before_id = request.GET.get("before")

    queryset = conversation.messages.select_related("sender").prefetch_related("attachments", "reactions", "receipts")
    
    if before_id:
        queryset = queryset.filter(pk__lt=before_id)

    messages = list(queryset.order_by("-pk")[:limit])
    messages.reverse()

    data = [serialize_message(message) for message in messages]
    return JsonResponse({"messages": data})



@login_required
@require_http_methods(["POST"])
def conversation_attachment_upload(request, pk):
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
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content="",
            message_type=Message.MessageType.ATTACHMENT,
        )
        MessageAttachment.objects.create(
            message=message,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            content_type=uploaded_file.content_type,
        )
        other_members = conversation.get_members().exclude(pk=request.user.pk)
        MessageReceipt.objects.bulk_create([
            MessageReceipt(message=message, user=member) for member in other_members
        ])
        _maybe_accept_conversation(conversation, request.user)
        conversation.touch()

    payload = serialize_message(message)
    
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"conversation_{conversation.pk}",
        {"type": "chat.message", "message": payload},
    )
    
    return JsonResponse(payload, status=201)







@login_required
@require_http_methods(["POST"])
def conversation_leave(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    membership = ConversationMember.objects.filter(conversation=conversation, user=request.user).first()
    if membership is None:
        return HttpResponseForbidden("You are not member of this conversation")
    membership.leave()
    return redirect("chat:conversation_list")
