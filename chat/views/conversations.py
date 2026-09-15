"""Vues de navigation, recherche et ouverture des conversations."""

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from ..models import Conversation
from .common import preview_text

User = get_user_model()


@login_required
def conversation_list(request):
    """Affiche les conversations visibles dans la boîte de réception de l'utilisateur."""
    conversations = Conversation.objects.for_user_inbox(request.user).order_by("-updated_at")
    items = []
    for conversation in conversations:
        other_user = conversation.get_members().exclude(pk=request.user.pk).first()
        items.append({"conversation": conversation, "other_user": other_user, "preview": preview_text(conversation.get_last_message())})
    invitations_count = Conversation.objects.invitations_for_user(request.user).count()
    return render(request, "chat/conversation_list.html", {"items": items, "invitations_count": invitations_count, "active_nav": "messages"})


@login_required
def invitations_list(request):
    """Affiche les invitations reçues qui attendent une première réponse."""
    conversations = Conversation.objects.invitations_for_user(request.user).order_by("-updated_at")
    items = []
    for conversation in conversations:
        first_message = conversation.messages.order_by("created_at").first()
        items.append({"conversation": conversation, "initiator": conversation.initiated_by, "preview": preview_text(first_message)})
    return render(request, "chat/invitations_list.html", {"items": items, "active_nav": "messages"})


@login_required
def user_search(request):
    """Rend l'interface de recherche ou les vingt premiers résultats AJAX."""
    query = (request.GET.get("q") or "").strip()
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if not is_ajax:
        return render(request, "chat/user_search.html", {"active_nav": "messages"})
    users = User.objects.filter(is_active=True).exclude(pk=request.user.pk)
    if query:
        users = users.filter(Q(username__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(email__icontains=query))
    users = users.order_by("username")[:20]
    return JsonResponse({"users": [{"id": u.id, "username": u.username} for u in users]})


@login_required
def conversation_start(request, user_id):
    """Crée ou retrouve une conversation privée puis redirige vers son détail."""
    target = get_object_or_404(User, pk=user_id)
    if target.pk == request.user.pk:
        return HttpResponseBadRequest(_("You cannot start a conversation with yourself."))
    conversation = Conversation.objects.get_or_create_private(request.user, target)
    return redirect("chat:conversation_detail", pk=conversation.pk)


@login_required
def conversation_detail(request, pk):
    """Affiche une conversation après avoir vérifié l'adhésion active de l'utilisateur."""
    conversation = get_object_or_404(Conversation, pk=pk)
    if not conversation.is_member(request.user):
        return HttpResponseForbidden(_("You are not a member of this conversation."))
    other_user = conversation.get_members().exclude(pk=request.user.pk).first()
    return render(request, "chat/conversation_detail.html", {"conversation": conversation, "other_user": other_user, "is_invitation": conversation.is_invitation_for(request.user), "active_nav": "messages"})
