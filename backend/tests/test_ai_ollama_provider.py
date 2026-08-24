import httpx
import pytest

from app.ai.ollama_provider import OllamaProvider
from app.ai.provider import AIProviderResponseError, AIProviderTimeoutError, AIProviderUnavailableError


def _provider_with_transport(transport):
    provider = OllamaProvider(base_url="http://localhost:11434", model="qwen2.5:3b")
    # Patch httpx.post/get used inside the provider to route through a
    # mock transport instead of a real socket -- no live Ollama needed.
    client = httpx.Client(transport=transport)

    def fake_post(url, json=None, timeout=None):
        return client.post(url, json=json, timeout=timeout)

    def fake_get(url, timeout=None):
        return client.get(url, timeout=timeout)

    return provider, fake_post, fake_get


def test_complete_returns_content_on_success(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"message": {"role": "assistant", "content": '{"ok": true}'}})

    provider, fake_post, _ = _provider_with_transport(httpx.MockTransport(handler))
    monkeypatch.setattr("app.ai.ollama_provider.httpx.post", fake_post)

    result = provider.complete("system", "user")
    assert result == '{"ok": true}'


def test_complete_raises_unavailable_on_connect_error(monkeypatch):
    def raise_connect_error(url, json=None, timeout=None):
        raise httpx.ConnectError("connection refused")

    provider = OllamaProvider(base_url="http://localhost:11434", model="qwen2.5:3b")
    monkeypatch.setattr("app.ai.ollama_provider.httpx.post", raise_connect_error)

    with pytest.raises(AIProviderUnavailableError):
        provider.complete("system", "user")


def test_complete_raises_timeout(monkeypatch):
    def raise_timeout(url, json=None, timeout=None):
        raise httpx.TimeoutException("timed out")

    provider = OllamaProvider(base_url="http://localhost:11434", model="qwen2.5:3b")
    monkeypatch.setattr("app.ai.ollama_provider.httpx.post", raise_timeout)

    with pytest.raises(AIProviderTimeoutError):
        provider.complete("system", "user")


def test_complete_raises_on_model_not_found(monkeypatch):
    def handler(request):
        return httpx.Response(404, json={"error": "model not found"})

    provider, fake_post, _ = _provider_with_transport(httpx.MockTransport(handler))
    monkeypatch.setattr("app.ai.ollama_provider.httpx.post", fake_post)

    with pytest.raises(AIProviderResponseError):
        provider.complete("system", "user")


def test_complete_raises_on_non_200_status(monkeypatch):
    def handler(request):
        return httpx.Response(500, text="internal error")

    provider, fake_post, _ = _provider_with_transport(httpx.MockTransport(handler))
    monkeypatch.setattr("app.ai.ollama_provider.httpx.post", fake_post)

    with pytest.raises(AIProviderResponseError):
        provider.complete("system", "user")


def test_complete_raises_on_malformed_json_body(monkeypatch):
    def handler(request):
        return httpx.Response(200, text="not json at all {{{")

    provider, fake_post, _ = _provider_with_transport(httpx.MockTransport(handler))
    monkeypatch.setattr("app.ai.ollama_provider.httpx.post", fake_post)

    with pytest.raises(AIProviderResponseError):
        provider.complete("system", "user")


def test_complete_raises_on_unexpected_response_shape(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"unexpected": "shape"})

    provider, fake_post, _ = _provider_with_transport(httpx.MockTransport(handler))
    monkeypatch.setattr("app.ai.ollama_provider.httpx.post", fake_post)

    with pytest.raises(AIProviderResponseError):
        provider.complete("system", "user")


def test_complete_raises_on_empty_content(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"message": {"role": "assistant", "content": "   "}})

    provider, fake_post, _ = _provider_with_transport(httpx.MockTransport(handler))
    monkeypatch.setattr("app.ai.ollama_provider.httpx.post", fake_post)

    with pytest.raises(AIProviderResponseError):
        provider.complete("system", "user")


def test_is_available_true_on_200(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"models": []})

    provider, _, fake_get = _provider_with_transport(httpx.MockTransport(handler))
    monkeypatch.setattr("app.ai.ollama_provider.httpx.get", fake_get)

    assert provider.is_available() is True


def test_is_available_false_when_unreachable(monkeypatch):
    def raise_connect_error(url, timeout=None):
        raise httpx.ConnectError("connection refused")

    provider = OllamaProvider(base_url="http://localhost:11434", model="qwen2.5:3b")
    monkeypatch.setattr("app.ai.ollama_provider.httpx.get", raise_connect_error)

    assert provider.is_available() is False
