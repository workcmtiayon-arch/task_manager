"""Application service coordinating context, persistence and providers."""

import json

from django.conf import settings

from .context import build_user_context
from .exceptions import AIConfigurationError
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
    context = json.dumps(build_user_context(user, project_id), ensure_ascii=False)
    return {"role": "system", "content": f"Contexte Task Manager autorisé : {context}"}


def chat(user, content, conversation=None, project_id=None):
    content = content.strip()
    if not content:
        raise ValueError("La demande ne peut pas être vide.")
    conversation = conversation or Conversation.objects.create(user=user, title=content[:120])
    history = list(conversation.messages.values("role", "content"))
    messages = [_context_message(user, project_id), *history, {"role": "user", "content": content}]
    provider = get_provider()
    answer = provider.complete(messages)
    Message.objects.create(conversation=conversation, role=Message.Role.USER, content=content)
    Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content=answer, provider=provider.name, model=provider.model)
    return conversation, answer
