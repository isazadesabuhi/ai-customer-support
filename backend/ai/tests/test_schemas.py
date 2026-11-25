import pytest

from ai.errors import LLMInvalidRequestError, LLMInvalidResponseError
from ai.schemas import LLMMessage, LLMResponse, LLMUsage, validate_request
from ai.testing import FakeLLMClient


@pytest.mark.parametrize("role", ["system", "developer", "user", "assistant"])
def test_messages_preserve_roles_and_exact_text(role):
    content = "  Example\ninput.  "
    message = LLMMessage(role, content)
    assert (message.role, message.content) == (role, content)


@pytest.mark.parametrize(
    "role, content", [("tool", "text"), ("user", ""), ("user", " \n"), ("user", 7)]
)
def test_invalid_message_rejected(role, content):
    with pytest.raises(LLMInvalidRequestError):
        LLMMessage(role, content)


@pytest.mark.parametrize(
    "options",
    [
        {"messages": []},
        {"messages": [{"role": "user", "content": "text"}]},
        {"model": ""},
        {"model": "two words"},
        {"max_output_tokens": 0},
        {"max_output_tokens": 4097},
        {"max_output_tokens": 20.5},
        {"max_output_tokens": True},
        {"temperature": -0.1},
        {"temperature": 2.01},
        {"temperature": float("nan")},
        {"temperature": float("inf")},
        {"temperature": "1"},
        {"temperature": True},
    ],
)
def test_invalid_request_values(options):
    valid = {
        "messages": [LLMMessage("user", "Hello")],
        "model": None,
        "temperature": None,
        "max_output_tokens": None,
    }
    with pytest.raises(LLMInvalidRequestError):
        validate_request(**(valid | options))


@pytest.mark.parametrize("count", [-1, True, 1.5, "8"])
def test_token_counts_are_nonnegative_integers(count):
    with pytest.raises(LLMInvalidResponseError):
        LLMUsage(input_tokens=count)


@pytest.mark.parametrize("text", ["Hello", ""])
def test_fake_can_replay_output_and_capture_immutable_request(text):
    response = LLMResponse(text=text, provider="fake", model="test-model")
    client = FakeLLMClient(response)
    messages = [LLMMessage("user", "Hello")]
    assert (
        client.generate(
            messages, model="other-model", temperature=0.25, max_output_tokens=64
        )
        == response
    )
    messages.clear()
    assert client.calls[0].messages == (LLMMessage("user", "Hello"),)
    assert (
        client.calls[0].model,
        client.calls[0].temperature,
        client.calls[0].max_output_tokens,
    ) == ("other-model", 0.25, 64)
    assert response.usage is None


def test_fake_can_simulate_provider_error():
    client = FakeLLMClient(LLMInvalidResponseError("Synthetic failure"))
    with pytest.raises(LLMInvalidResponseError, match="Synthetic failure"):
        client.generate([LLMMessage("user", "Hello")])
    assert len(client.calls) == 1
