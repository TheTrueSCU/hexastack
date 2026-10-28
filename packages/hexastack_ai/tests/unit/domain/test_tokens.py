from hexastack_ai.domain.tokens import (
    MODEL_BUDGET_CATALOG,
    ChatMessage,
    ModelBudget,
    TokenUsage,
    get_model_budget,
)


def test_chat_message_to_dict():
    msg = ChatMessage(role="user", content="Hello world")
    d = msg.to_dict()
    assert d == {"role": "user", "content": "Hello world"}

    tool_msg = ChatMessage(role="tool", content="42", name="calculator")
    tool_d = tool_msg.to_dict()
    assert tool_d == {"role": "tool", "content": "42", "name": "calculator"}


def test_token_usage_arithmetic():
    u1 = TokenUsage(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost_usd=0.002,
    )
    u2 = TokenUsage(
        prompt_tokens=200,
        completion_tokens=100,
        total_tokens=300,
        estimated_cost_usd=0.004,
    )

    combined = u1 + u2
    assert combined.prompt_tokens == 300
    assert combined.completion_tokens == 150
    assert combined.total_tokens == 450
    assert combined.estimated_cost_usd is not None
    assert round(combined.estimated_cost_usd, 6) == 0.006

    # Test None cost addition
    u3 = TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20)
    u4 = TokenUsage(prompt_tokens=20, completion_tokens=20, total_tokens=40)
    comb_none = u3 + u4
    assert comb_none.estimated_cost_usd is None


def test_model_budget_calculations():
    budget = ModelBudget(
        model="test-model",
        max_context_tokens=100_000,
        max_output_tokens=4_000,
        prompt_cost_per_million=2.00,
        completion_cost_per_million=8.00,
    )

    cost = budget.calculate_cost(prompt_tokens=500_000, completion_tokens=250_000)
    # (500k * 2.00 + 250k * 8.00) / 1M = (1.00 + 2.00) = 3.00
    assert round(cost, 2) == 3.00

    avail = budget.available_context_tokens(reserved_output_tokens=4_000)
    assert avail == 96_000

    over_reserved = budget.available_context_tokens(reserved_output_tokens=120_000)
    assert over_reserved == 0


def test_get_model_budget_resolution():
    gpt4o = get_model_budget("gpt-4o")
    assert gpt4o.model == "gpt-4o"
    assert gpt4o.max_context_tokens == 128_000

    # Prefix resolution
    prefixed = get_model_budget("openai/gpt-4o")
    assert prefixed.model == "gpt-4o"

    claude = get_model_budget("anthropic/claude-3-5-sonnet")
    assert claude.model == "claude-3-5-sonnet"
    assert claude.max_context_tokens == 200_000

    gemini = get_model_budget("gemini/gemini-1.5-pro")
    assert gemini.model == "gemini-1.5-pro"
    assert gemini.max_context_tokens == 2_097_152

    # Fallback default
    unknown = get_model_budget("custom-finetuned-model-v9")
    assert unknown.model == "custom-finetuned-model-v9"
    assert unknown.max_context_tokens == 128_000


def test_model_budget_catalog_contains_standard_models():
    assert "gpt-4o" in MODEL_BUDGET_CATALOG
    assert "claude-3-5-sonnet" in MODEL_BUDGET_CATALOG
    assert "gemini-1.5-flash" in MODEL_BUDGET_CATALOG
    assert "llama-3.1-70b" in MODEL_BUDGET_CATALOG
