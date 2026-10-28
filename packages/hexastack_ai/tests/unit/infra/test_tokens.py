from unittest.mock import MagicMock

from hexastack_ai.domain.tokens import ChatMessage
from hexastack_ai.infra.tokens import TokenBudgetManager


def test_token_budget_manager_initialization():
    mgr = TokenBudgetManager()
    assert mgr.tokenizer is not None
    assert mgr.telemetry_hook is not None


def test_token_budget_manager_get_budget():
    mgr = TokenBudgetManager()
    budget = mgr.get_budget("gpt-4o")
    assert budget.model == "gpt-4o"
    assert budget.max_context_tokens == 128_000


def test_token_budget_manager_calculate_usage():
    mgr = TokenBudgetManager()
    usage = mgr.calculate_usage(
        prompt_tokens=1000, completion_tokens=500, model="gpt-4o"
    )
    assert usage.prompt_tokens == 1000
    assert usage.completion_tokens == 500
    assert usage.total_tokens == 1500
    assert usage.estimated_cost_usd is not None
    assert usage.estimated_cost_usd > 0


def test_token_budget_manager_prepare_messages():
    mgr = TokenBudgetManager()
    messages = [
        ChatMessage(role="system", content="System instruction."),
        ChatMessage(role="user", content="Turn 1 with details."),
        ChatMessage(role="assistant", content="Turn 2 reply."),
        ChatMessage(role="user", content="Turn 3 latest prompt."),
    ]

    pruned, usage = mgr.prepare_messages(
        messages=messages,
        model="gpt-4o",
        max_context_tokens=35,
        strategy="oldest_first",
    )

    assert len(pruned) >= 1
    assert pruned[0].role == "system"
    assert usage.prompt_tokens > 0
    assert usage.completion_tokens == 0
    assert usage.total_tokens == usage.prompt_tokens


def test_token_budget_manager_record_usage():
    mock_hook = MagicMock()
    mgr = TokenBudgetManager(telemetry_hook=mock_hook)

    usage = mgr.record_usage(
        prompt_tokens=200,
        completion_tokens=80,
        model="claude-3-5-sonnet",
        attributes={"session_id": "sess-42"},
    )

    assert usage.prompt_tokens == 200
    assert usage.completion_tokens == 80
    assert usage.total_tokens == 280
    mock_hook.record_usage.assert_called_once_with(
        usage,
        "claude-3-5-sonnet",
        attributes={"session_id": "sess-42"},
    )
