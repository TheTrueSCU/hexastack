from unittest.mock import MagicMock, patch

import pytest

from hexastack_ai.adapters.tokens import LocalTokenizerAdapter, TokenTelemetryHook
from hexastack_ai.domain.exceptions import (
    TokenizerNotFoundError,
    TokenLimitExceededError,
)
from hexastack_ai.domain.tokens import ChatMessage, TokenUsage


def test_local_tokenizer_count_tokens_openai():
    adapter = LocalTokenizerAdapter(default_model="gpt-4o")
    count = adapter.count_tokens(
        "Hello, world! This is a test sentence.", model="gpt-4o"
    )
    assert count > 0

    # Test cache hit on second call
    count_cached = adapter.count_tokens("Hello again!", model="gpt-4o")
    assert count_cached > 0

    empty_count = adapter.count_tokens("")
    assert empty_count == 0


def test_local_tokenizer_count_tokens_claude_and_gemini_calibration():
    adapter = LocalTokenizerAdapter()
    text = "The quick brown fox jumps over the lazy dog."

    gpt_tokens = adapter.count_tokens(text, model="gpt-4o")
    claude_tokens = adapter.count_tokens(text, model="claude-3-5-sonnet")
    gemini_tokens = adapter.count_tokens(text, model="gemini-1.5-pro")

    assert gpt_tokens > 0
    assert claude_tokens >= gpt_tokens
    assert gemini_tokens >= gpt_tokens


def test_local_tokenizer_count_messages_tokens():
    adapter = LocalTokenizerAdapter(default_model="gpt-4o")
    messages = [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="Hello, what is 2+2?", name="User1"),
        {"role": "assistant", "content": "4"},  # Raw dictionary normalization
    ]

    count = adapter.count_messages_tokens(messages, model="gpt-4o")
    assert count > 15

    empty_count = adapter.count_messages_tokens([], model="gpt-4o")
    assert empty_count == 0


def test_local_tokenizer_prune_no_op_when_under_budget():
    adapter = LocalTokenizerAdapter(default_model="gpt-4o")
    messages = [
        ChatMessage(role="system", content="Short system."),
        ChatMessage(role="user", content="Short user."),
    ]
    pruned = adapter.prune_messages(messages, max_tokens=1000)
    assert len(pruned) == 2


def test_local_tokenizer_prune_empty_list():
    adapter = LocalTokenizerAdapter()
    pruned = adapter.prune_messages([], max_tokens=100)
    assert len(pruned) == 0


def test_local_tokenizer_prune_preserve_system_false():
    adapter = LocalTokenizerAdapter(default_model="gpt-4o")
    messages = [
        ChatMessage(role="system", content="System msg 1"),
        ChatMessage(role="user", content="User msg 2"),
        ChatMessage(role="assistant", content="Assistant msg 3"),
    ]
    pruned = adapter.prune_messages(
        messages=messages,
        max_tokens=15,
        preserve_system=False,
    )
    assert len(pruned) <= len(messages)


def test_local_tokenizer_prune_oldest_first_all_dropped():
    adapter = LocalTokenizerAdapter(default_model="gpt-4o")
    system_msg = ChatMessage(role="system", content="Keep system.")
    messages = [
        system_msg,
        ChatMessage(role="user", content="Drop turn 1 with some words"),
        ChatMessage(role="assistant", content="Drop turn 2 with some words"),
    ]

    sys_tokens = adapter.count_messages_tokens([system_msg])
    # Budget only allows system message
    pruned = adapter.prune_messages(
        messages, max_tokens=sys_tokens, strategy="oldest_first"
    )
    assert len(pruned) == 1
    assert pruned[0].role == "system"


def test_local_tokenizer_prune_keep_system_and_last_n_all_dropped():
    adapter = LocalTokenizerAdapter(default_model="gpt-4o")
    system_msg = ChatMessage(role="system", content="Keep system.")
    messages = [
        system_msg,
        ChatMessage(role="user", content="Turn 1"),
        ChatMessage(role="assistant", content="Turn 2"),
    ]

    sys_tokens = adapter.count_messages_tokens([system_msg])
    pruned = adapter.prune_messages(
        messages, max_tokens=sys_tokens, strategy="keep_system_and_last_n"
    )
    assert len(pruned) == 1
    assert pruned[0].role == "system"


def test_local_tokenizer_prune_trim_exact():
    adapter = LocalTokenizerAdapter(default_model="gpt-4o")
    system_msg = ChatMessage(role="system", content="Base system.")
    long_history = ChatMessage(
        role="user",
        content="This is an extremely long story about a wanderer who travelled across seven seas and climbed mountains.",
    )
    latest_msg = ChatMessage(role="user", content="Short query.")

    messages = [system_msg, long_history, latest_msg]
    sys_and_latest_tokens = adapter.count_messages_tokens([system_msg, latest_msg])
    target_budget = sys_and_latest_tokens + 10

    pruned = adapter.prune_messages(
        messages=messages,
        max_tokens=target_budget,
        strategy="trim_token_exact",
        preserve_system=True,
    )

    final_tokens = adapter.count_messages_tokens(pruned)
    assert final_tokens <= target_budget
    assert len(pruned) == 3
    assert pruned[1].content.endswith("...")


def test_local_tokenizer_prune_trim_exact_no_conversation():
    adapter = LocalTokenizerAdapter(default_model="gpt-4o")
    system_msg = ChatMessage(role="system", content="Only system.")
    pruned = adapter.prune_messages(
        [system_msg], max_tokens=100, strategy="trim_token_exact"
    )
    assert len(pruned) == 1


def test_local_tokenizer_prune_trim_exact_allowance_too_small():
    adapter = LocalTokenizerAdapter(default_model="gpt-4o")
    system_msg = ChatMessage(role="system", content="Sys.")
    user_msg = ChatMessage(role="user", content="Turn.")
    messages = [system_msg, user_msg]
    # Set max_tokens to exact system message length
    sys_tokens = adapter.count_messages_tokens([system_msg])
    pruned = adapter.prune_messages(
        messages, max_tokens=sys_tokens, strategy="trim_token_exact"
    )
    assert len(pruned) == 1
    assert pruned[0].role == "system"


def test_local_tokenizer_system_exceeds_budget_raises():
    adapter = LocalTokenizerAdapter(default_model="gpt-4o")
    system_msg = ChatMessage(
        role="system",
        content="A long system prompt that alone consumes more tokens than permitted.",
    )
    messages = [system_msg, ChatMessage(role="user", content="hi")]

    with pytest.raises(TokenLimitExceededError) as exc_info:
        adapter.prune_messages(messages, max_tokens=5, preserve_system=True)

    err = exc_info.value
    assert err.max_tokens == 5
    assert err.current_tokens > 5


def test_local_tokenizer_resolve_encoding_failure():
    adapter = LocalTokenizerAdapter()
    with (
        patch("tiktoken.get_encoding", side_effect=Exception("Encoding unavailable")),
        pytest.raises(TokenizerNotFoundError),
    ):
        adapter.count_tokens("test", model="unsupported-model-xyz")


def test_local_tokenizer_custom_tokenizer_mock():
    mock_tokenizer = MagicMock()
    mock_encoding = MagicMock()
    mock_encoding.ids = [101, 102, 103, 104]
    mock_tokenizer.encode.return_value = mock_encoding

    adapter = LocalTokenizerAdapter(custom_tokenizer=mock_tokenizer)
    count = adapter.count_tokens("Custom tokenized text")
    assert count == 4
    mock_tokenizer.encode.assert_called_once_with("Custom tokenized text")


def test_local_tokenizer_from_path(tmp_path):
    # Test tokenizer_path argument branch
    fake_tokenizer_file = tmp_path / "tokenizer.json"
    fake_tokenizer_file.write_text('{"version": "1.0"}')

    with patch("tokenizers.Tokenizer.from_file") as mock_from_file:
        mock_from_file.return_value = MagicMock()
        adapter = LocalTokenizerAdapter(tokenizer_path=fake_tokenizer_file)
        assert adapter._custom_tokenizer is not None
        mock_from_file.assert_called_once_with(str(fake_tokenizer_file))


def test_local_tokenizer_estimate_cost():
    adapter = LocalTokenizerAdapter()
    cost = adapter.estimate_cost(
        prompt_tokens=1_000_000, completion_tokens=1_000_000, model="gpt-4o"
    )
    assert round(cost, 2) == 12.50


def test_token_telemetry_hook_logging_and_otel():
    mock_logger = MagicMock()
    hook = TokenTelemetryHook(logger=mock_logger, enable_otel=True)

    usage = TokenUsage(
        prompt_tokens=150,
        completion_tokens=50,
        total_tokens=200,
        estimated_cost_usd=0.0015,
    )
    hook.record_usage(usage, model="gpt-4o", attributes={"user_id": "u123"})

    mock_logger.info.assert_called_once()
    call_args, call_kwargs = mock_logger.info.call_args
    assert call_args[0] == "LLM token usage recorded"
    assert call_kwargs["extra"]["model"] == "gpt-4o"
    assert call_kwargs["extra"]["prompt_tokens"] == 150
    assert call_kwargs["extra"]["user_id"] == "u123"


def test_token_telemetry_hook_otel_disabled():
    mock_logger = MagicMock()
    hook = TokenTelemetryHook(logger=mock_logger, enable_otel=False)
    assert hook._prompt_counter is None

    usage = TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20)
    hook.record_usage(usage, model="test-model")
    mock_logger.info.assert_called_once()


def test_token_telemetry_hook_otel_init_exception():
    with patch(
        "opentelemetry.metrics.get_meter", side_effect=RuntimeError("Meter failed")
    ):
        hook = TokenTelemetryHook(enable_otel=True)
        assert hook._prompt_counter is None
