import json
import logging
import hashlib

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.cache import cache
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .exceptions import AIError
from .models import Conversation
from .services import chat
from projects.models import Project

logger = logging.getLogger(__name__)


def csrf_failure(request, reason=""):
    return JsonResponse({"detail": "Session expirée ou jeton CSRF invalide."}, status=403)


@login_required
@require_POST
@never_cache
def chat_view(request):
    try:
        payload = json.loads(request.body or "{}")
        if not isinstance(payload, dict):
            return JsonResponse({"detail": "Demande invalide."}, status=400)
        rate_key = "ai-chat:" + hashlib.sha256(
            str(request.user.pk).encode()
        ).hexdigest()
        attempts = cache.get(rate_key, 0)
        if attempts >= getattr(settings, "AI_RATE_LIMIT_ATTEMPTS", 10):
            return JsonResponse({"detail": "Limite de requêtes atteinte. Réessaie plus tard."}, status=429)
        window = getattr(settings, "AI_RATE_LIMIT_WINDOW_SECONDS", 3600)
        if not cache.add(rate_key, 1, window):
            try:
                attempts = cache.incr(rate_key)
            except ValueError:
                cache.add(rate_key, 1, window)
                attempts = 1
            if attempts > getattr(settings, "AI_RATE_LIMIT_ATTEMPTS", 10):
                return JsonResponse({"detail": "Limite de requêtes atteinte. Réessaie plus tard."}, status=429)
        content = payload.get("content", "")
        if not isinstance(content, str) or len(content) > 4000:
            return JsonResponse({"detail": "La demande est invalide ou trop longue."}, status=400)
        conversation = None
        conversation_id = payload.get("conversation_id")
        if conversation_id is not None:
            try:
                conversation_id = int(conversation_id)
            except (TypeError, ValueError):
                return JsonResponse({"detail": "Demande invalide."}, status=400)
            conversation = Conversation.objects.get(pk=conversation_id, user=request.user)
        project_id = payload.get("project_id")
        if project_id is not None:
            try:
                project_id = int(project_id)
            except (TypeError, ValueError):
                return JsonResponse({"detail": "Demande invalide."}, status=400)
        if project_id is not None and not Project.objects.filter(
            pk=project_id, user=request.user
        ).exists():
            return JsonResponse({"detail": "Projet introuvable."}, status=404)
        conversation, answer = chat(request.user, content, conversation, project_id)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"detail": "Demande invalide."}, status=400)
    except Conversation.DoesNotExist:
        return JsonResponse({"detail": "Conversation introuvable."}, status=404)
    except AIError as exc:
        return JsonResponse({"detail": str(exc)}, status=503)
    except Exception as exc:
        logger.exception("Unexpected error while processing an AI request")
        detail = "Erreur Gemini inattendue. Consulte les logs du serveur."
        if settings.DEBUG:
            detail = f"Erreur Gemini inattendue : {exc}"
        return JsonResponse({"detail": detail}, status=500)
    return JsonResponse({"conversation_id": conversation.pk, "answer": answer})
