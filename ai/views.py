import json
import logging
import hashlib

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .exceptions import AIError
from .models import Conversation
from .services import chat
from projects.models import Project
from core.security import increment_rate_limit

logger = logging.getLogger(__name__)


def csrf_failure(request, reason=""):
    return JsonResponse({"detail": "Session expirée ou jeton CSRF invalide."}, status=403)


@login_required
@require_POST
@never_cache
def chat_view(request):
    try:
        max_request_bytes = getattr(settings, "AI_MAX_REQUEST_BYTES", 65536)
        try:
            content_length = int(request.META.get("CONTENT_LENGTH") or 0)
        except (TypeError, ValueError):
            return JsonResponse({"detail": "Demande invalide."}, status=400)
        if content_length > max_request_bytes:
            return JsonResponse({"detail": "La demande est trop volumineuse."}, status=413)
        try:
            raw_body = request.body
        except RequestDataTooBig:
            return JsonResponse({"detail": "La demande est trop volumineuse."}, status=413)
        if len(raw_body) > max_request_bytes:
            return JsonResponse({"detail": "La demande est trop volumineuse."}, status=413)
        payload = json.loads(raw_body or "{}")
        if not isinstance(payload, dict):
            return JsonResponse({"detail": "Demande invalide."}, status=400)
        rate_key = "ai-chat:" + hashlib.sha256(
            str(request.user.pk).encode()
        ).hexdigest()
        window = getattr(settings, "AI_RATE_LIMIT_WINDOW_SECONDS", 3600)
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
        attempts = increment_rate_limit(rate_key, window)
        if attempts > getattr(settings, "AI_RATE_LIMIT_ATTEMPTS", 10):
            return JsonResponse({"detail": "Limite de requêtes atteinte. Réessaie plus tard."}, status=429)
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
