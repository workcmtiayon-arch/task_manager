"""Errors raised while communicating with an AI provider."""


class AIError(Exception):
    """Base error exposed by the AI service layer."""


class AIConfigurationError(AIError):
    """Raised when the selected provider is not configured correctly."""


class AIProviderError(AIError):
    """Raised when a provider rejects or cannot process a request."""
