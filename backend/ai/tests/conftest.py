import httpx
import pytest


@pytest.fixture
def llm_env(monkeypatch):
    for name in (
        "LLM_PROVIDER",
        "LLM_TIMEOUT_SECONDS",
        "LLM_MAX_RETRIES",
        "LLM_MAX_OUTPUT_TOKENS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-secret")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    return monkeypatch


@pytest.fixture(autouse=True)
def forbid_real_http(monkeypatch):
    def reject(self, request):
        pytest.fail("An LLM test attempted to use the network.")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", reject)
