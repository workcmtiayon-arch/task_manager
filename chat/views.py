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






@login_required
def conversation_list(request):
    memberships = (
        ConversationMember.objects.filter(user=request.user, left_at__isnull=True)
        .select_related("conversation")
        .order_by("-conversation__updated_at")
    )
    conversations = [m.conversation for m in memberships]
    return render(request, "chat/conversation_list.html", {"conversations": conversations})



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
        return HttpResponseForbidden("Vous n'êtes pas membre de cette conversation.")
    return render(request, "chat/conversation_detail.html", {"conversation": conversation})


@login_required
def conversation_messages_json(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.is_member(request.user):
        return HttpResponseForbidden("Vous n'êtes pas membre de cette conversation.")

    limit = min(int(request.GET.get("limit", 50)), 100)
    before_id = request.GET.get("before")

    queryset = conversation.messages.select_related("sender").prefetch_related("attachments", "reactions", "receipts")
    
    if before_id:
        queryset = queryset.filter(pk__lt=before_id)

    messages = list(queryset.order_by("-pk")[:limit])
    messages.reverse()

    data = [serialize_message(message, for_user=request.user) for message in messages]
    return JsonResponse({"messages": data})

