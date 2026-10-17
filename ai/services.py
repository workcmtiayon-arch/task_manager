"""Application service coordinating context, persistence and providers."""

import json

from django.conf import settings

from .context import build_user_context
from .exceptions import AIConfigurationError, AIProviderError
from .models import Conversation, Message
from .providers import GeminiProvider, OpenAIProvider


def get_provider():
    provider_name = settings.AI_PROVIDER
    if not settings.AI_API_KEY:
        raise AIConfigurationError("Aucune clé API AI n'est configurée.")
    provider_class = {"gemini": GeminiProvider, "openai": OpenAIProvider}.get(provider_name)
    if provider_class is None:
        raise AIConfigurationError("Le fournisseur AI configuré est invalide.")
    return provider_class(settings.AI_API_KEY, settings.AI_MODEL, settings.AI_API_TIMEOUT)


def _context_message(user, project_id=None):
    projects = build_user_context(user, project_id)
    context = json.dumps(projects, ensure_ascii=False)
    # Remove the least recent context until the serialized document fits. This
    # keeps the JSON valid while bounding provider input for large workspaces.
    while len(context) > settings.AI_MAX_CONTEXT_CHARS and projects:
        last_project = projects[-1]
        if last_project["tasks"]:
            last_project["tasks"].pop()
        else:
            projects.pop()
        context = json.dumps(projects, ensure_ascii=False)
    return {"role": "system", "content": f"Contexte Task Manager autorisé : {context}"}


def chat(user, content, conversation=None, project_id=None):
    content = content.strip()
    if not content or len(content) > settings.AI_MAX_INPUT_CHARS:
        raise ValueError("La demande est vide ou trop longue.")
    history = []
    if conversation is not None:
        history = list(
            conversation.messages.order_by("-created_at", "-pk")
            .values("role", "content")[:settings.AI_MAX_HISTORY_MESSAGES]
        )
        bounded_history = []
        history_chars = 0
        for item in history:
            item_chars = len(item["content"])
            if history_chars + item_chars > settings.AI_MAX_HISTORY_CHARS:
                break
            bounded_history.append(item)
            history_chars += item_chars
        history = list(reversed(bounded_history))
    messages = [_context_message(user, project_id), *history, {"role": "user", "content": content}]
    provider = get_provider()
    answer = provider.complete(messages)
    if not isinstance(answer, str) or len(answer) > settings.AI_MAX_OUTPUT_CHARS:
        raise AIProviderError("La réponse AI dépasse la taille autorisée.")
    from django.db import transaction
    with transaction.atomic():
        if conversation is None:
            conversation = Conversation.objects.create(user=user, title=content[:120])
        Message.objects.create(conversation=conversation, role=Message.Role.USER, content=content)
        Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content=answer, provider=provider.name, model=provider.model)
    return conversation, answer
