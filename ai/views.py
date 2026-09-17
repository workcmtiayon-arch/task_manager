import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .exceptions import AIError
from .models import Conversation
from .services import chat


@login_required
@require_POST
def chat_view(request):
    try:
        payload = json.loads(request.body or "{}")
        content = str(payload.get("content", ""))[:4000]
        conversation = None
        if payload.get("conversation_id"):
            conversation = Conversation.objects.get(pk=payload["conversation_id"], user=request.user)
        project_id = payload.get("project_id")
        conversation, answer = chat(request.user, content, conversation, project_id)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"detail": "Demande invalide."}, status=400)
    except Conversation.DoesNotExist:
        return JsonResponse({"detail": "Conversation introuvable."}, status=404)
    except AIError as exc:
        return JsonResponse({"detail": str(exc)}, status=503)
    return JsonResponse({"conversation_id": conversation.pk, "answer": answer})
