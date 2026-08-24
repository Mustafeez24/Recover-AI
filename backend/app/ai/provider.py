"""The AI provider abstraction.

Business logic (app.ai.service) depends on this narrow interface, never
on Ollama specifically, so a different local or hosted provider could be
added later without touching the recovery system. The interface only
covers transport: "given a system + user prompt, return the model's raw
text". Parsing/validating the *content* of that text happens above this
layer.
"""

from abc import ABC, abstractmethod


class AIProviderError(Exception):
    """Base class for AI provider failures."""


class AIProviderUnavailableError(AIProviderError):
    """The provider could not be reached at all (connection refused, DNS
    failure, etc.)."""


class AIProviderTimeoutError(AIProviderError):
    """The provider did not respond within the configured timeout."""


class AIProviderResponseError(AIProviderError):
    """The provider responded, but with something unusable: a non-2xx
    status, a missing model, malformed JSON, an unexpected response shape,
    or empty content."""


class AIProvider(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return the model's raw text completion, or raise one of the
        AIProviderError subtypes above."""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """A cheap connectivity check -- must not invoke generation, must
        never raise."""
        raise NotImplementedError
