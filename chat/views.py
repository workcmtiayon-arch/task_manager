from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q

from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Conversation, ConversationMember, Message, MessageAttachment, MessageReaction, MessageReceipt
from .utils import serialize_message, serialize_reactions

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
    if conversation.accepted_at is None and sender.id != conversation.initiated_by_id:
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
        "active_nav": "messages",
    })
    
@login_required
def invitations_list(request):
    conversations = Conversation.objects.invitations_for_user(request.user).order_by("-updated_at")
    items = []
    for conversation in conversations:
        first_message = conversation.messages.order_by("created_at").first()
        items.append({
            "conversation": conversation,
            "initiator": conversation.initiated_by,
            "preview": _preview_text(first_message),
        })
    return render(request, "chat/invitations_list.html", {
        "items": items,
        "active_nav": "messages",
    })


@login_required
def user_search(request):
    query = (request.GET.get("q") or "").strip()
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    # L'URL ouverte dans le navigateur affiche l'interface. Seules les
    # requêtes JavaScript reçoivent la réponse JSON consommée par le script.
    if not is_ajax:
        return render(request, "chat/user_search.html", {"active_nav": "messages"})

    users = User.objects.filter(is_active=True).exclude(pk=request.user.pk)
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )
    users = users.order_by("username")[:20]
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
        "active_nav": "messages",
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
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            message_type=Message.MessageType.TEXT,
        )
        other_members = conversation.get_members().exclude(pk=request.user.pk)
        MessageReceipt.objects.bulk_create([
            MessageReceipt(message=message, user=member) for member in other_members
        ])
        _maybe_accept_conversation(conversation, request.user)
        conversation.touch()

    payload = serialize_message(message)
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"conversation_{conversation.pk}",
            {"type": "chat.message", "message": payload},
        )
    except Exception:
        # Le message est déjà enregistré : Redis ne doit pas faire échouer
        # l'envoi ni empêcher le destinataire de le voir dans ses invitations.
        pass

    return JsonResponse(payload, status=201)



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


def _reaction_message(request, pk, remove=False):
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.is_member(request.user):
        return HttpResponseForbidden("Vous n'êtes pas membre de cette conversation.")
    message = get_object_or_404(Message, pk=request.POST.get("message_id"), conversation=conversation)
    if remove:
        MessageReaction.objects.filter(message=message, user=request.user).delete()
    else:
        reaction_value = request.POST.get("reaction")
        valid_values = [choice[0] for choice in MessageReaction.Reaction.choices]
        if reaction_value not in valid_values:
            return JsonResponse({"detail": "Réaction invalide."}, status=400)
        reaction, created = MessageReaction.objects.get_or_create(
            message=message, user=request.user, defaults={"reaction": reaction_value},
        )
        if not created:
            reaction.change(reaction_value)
    reactions = serialize_reactions(message)
    try:
        async_to_sync(get_channel_layer().group_send)(
            f"conversation_{conversation.pk}",
            {"type": "chat.reaction_update", "message_id": message.pk, "reactions": reactions},
        )
    except Exception:
        pass
    return JsonResponse({"message_id": message.pk, "reactions": reactions})


@login_required
@require_http_methods(["POST"])
def conversation_reaction_set(request, pk):
    return _reaction_message(request, pk)


@login_required
@require_http_methods(["POST"])
def conversation_reaction_remove(request, pk):
    return _reaction_message(request, pk, remove=True)
