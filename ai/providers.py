"""Provider contract and HTTP implementations for the AI module."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .exceptions import AIProviderError


class BaseProvider:
    name = "unknown"

    def __init__(self, api_key, model, timeout=30):
        self.api_key, self.model, self.timeout = api_key, model, timeout

    def _post(self, url, payload, headers):
        request = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise AIProviderError("Le fournisseur AI est momentanément indisponible.") from exc

    def complete(self, messages):
        raise NotImplementedError


class OpenAIProvider(BaseProvider):
    name = "openai"

    def complete(self, messages):
        data = self._post("https://api.openai.com/v1/chat/completions", {"model": self.model, "messages": messages}, {"Authorization": f"Bearer {self.api_key}"})
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("Réponse AI invalide.") from exc


class GeminiProvider(BaseProvider):
    name = "gemini"

    def complete(self, messages):
        contents = [{"role": "user" if item["role"] == "user" else "model", "parts": [{"text": item["content"]}]} for item in messages]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        data = self._post(url, {"contents": contents}, {})
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("Réponse AI invalide.") from exc
