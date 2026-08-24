"""Local Ollama HTTP API provider. No API key -- it's a local server.
Uses httpx (already a project dependency) rather than adding a new one.
"""

import httpx

from app.ai.provider import (
    AIProvider,
    AIProviderResponseError,
    AIProviderTimeoutError,
    AIProviderUnavailableError,
)


class OllamaProvider(AIProvider):
    def __init__(self, base_url: str, model: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "format": "json",
                    "stream": False,
                },
                timeout=self.timeout,
            )
        except httpx.ConnectError as exc:
            raise AIProviderUnavailableError(
                f"Could not connect to Ollama at {self.base_url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise AIProviderTimeoutError(
                f"Ollama request timed out after {self.timeout}s: {exc}"
            ) from exc
        except httpx.HTTPError as exc:
            raise AIProviderUnavailableError(f"Ollama request failed: {exc}") from exc

        if response.status_code == 404:
            raise AIProviderResponseError(
                f"Model '{self.model}' not found on Ollama (404). "
                f"Pull it first with `ollama pull {self.model}`."
            )
        if response.status_code != 200:
            raise AIProviderResponseError(
                f"Ollama returned HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AIProviderResponseError(f"Ollama response was not valid JSON: {exc}") from exc

        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, dict) or "content" not in message:
            raise AIProviderResponseError(f"Unexpected Ollama response shape: {str(payload)[:300]}")

        content = message["content"]
        if not isinstance(content, str) or not content.strip():
            raise AIProviderResponseError("Ollama returned an empty response.")

        return content

    def is_available(self) -> bool:
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=3.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False
