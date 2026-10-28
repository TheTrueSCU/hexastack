"""Domain entities and value objects for token counting, context budgeting, and pruning.

Notes/Architectural Intent:
    Encapsulates immutable models representing chat messages, token consumption,
    model context budgets, and context window pruning strategies without coupling
    to external network providers or specific tokenizer runtime libraries.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

PruneStrategy = Literal["oldest_first", "keep_system_and_last_n", "trim_token_exact"]


class ChatMessage(BaseModel):
    """Represents a conversational message exchanged in an LLM dialog turn.

    Notes/Architectural Intent:
        Standardizes chat turns across diverse LLM provider formats (OpenAI, Anthropic,
        Gemini) for deterministic local token counting and message pruning.
    """

    role: str = Field(
        description="Role of the message author (e.g. 'system', 'user', 'assistant', 'tool')."
    )
    content: str = Field(description="Raw text content of the message.")
    name: str | None = Field(
        default=None,
        description="Optional name identifier for tool calls or participants.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata annotations attached to this turn.",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary compatible with LLM provider APIs.

        Returns:
            Dictionary containing role and content (and name if specified).
        """
        payload: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name is not None:
            payload["name"] = self.name
        return payload


class TokenUsage(BaseModel):
    """Value object capturing token counts and estimated operational cost.

    Notes/Architectural Intent:
        Represents measured or estimated LLM usage metrics. Supports arithmetic
        addition for cumulative session budgeting and reporting.
    """

    prompt_tokens: int = Field(
        default=0, ge=0, description="Tokens consumed by input prompts and context."
    )
    completion_tokens: int = Field(
        default=0, ge=0, description="Tokens generated in LLM completions."
    )
    total_tokens: int = Field(
        default=0, ge=0, description="Sum of prompt and completion tokens."
    )
    estimated_cost_usd: float | None = Field(
        default=None,
        ge=0.0,
        description="Estimated operational expense in USD.",
    )

    def __add__(self, other: TokenUsage) -> TokenUsage:
        """Combine two TokenUsage records additively.

        Args:
            other: Another TokenUsage instance to add.

        Returns:
            A new TokenUsage instance representing cumulative usage.
        """
        cost: float | None = None
        if self.estimated_cost_usd is not None or other.estimated_cost_usd is not None:
            cost = (self.estimated_cost_usd or 0.0) + (other.estimated_cost_usd or 0.0)
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            estimated_cost_usd=cost,
        )


class ModelBudget(BaseModel):
    """Specification of token context limits, output ceilings, and pricing for an LLM.

    Notes/Architectural Intent:
        Codifies hardware context constraints and billing rates to enable local
        pre-flight context budgeting and cost forecasting.
    """

    model: str = Field(description="Canonical model identifier.")
    max_context_tokens: int = Field(
        gt=0, description="Maximum total context window capacity in tokens."
    )
    max_output_tokens: int = Field(
        gt=0, description="Maximum completion generation output tokens."
    )
    prompt_cost_per_million: float = Field(
        default=0.0,
        ge=0.0,
        description="Cost in USD per 1,000,000 prompt tokens.",
    )
    completion_cost_per_million: float = Field(
        default=0.0,
        ge=0.0,
        description="Cost in USD per 1,000,000 completion tokens.",
    )

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Compute estimated cost in USD for the given token consumption.

        Args:
            prompt_tokens: Number of prompt tokens processed.
            completion_tokens: Number of completion tokens generated.

        Returns:
            Calculated cost in USD.
        """
        prompt_cost = (prompt_tokens * self.prompt_cost_per_million) / 1_000_000.0
        completion_cost = (
            completion_tokens * self.completion_cost_per_million
        ) / 1_000_000.0
        return prompt_cost + completion_cost

    def available_context_tokens(self, reserved_output_tokens: int = 0) -> int:
        """Calculate maximum tokens available for prompt history given reserved output tokens.

        Args:
            reserved_output_tokens: Expected completion tokens to reserve from context.

        Returns:
            Net context tokens available for input prompts.
        """
        return max(0, self.max_context_tokens - reserved_output_tokens)


MODEL_BUDGET_CATALOG: dict[str, ModelBudget] = {
    "gpt-4o": ModelBudget(
        model="gpt-4o",
        max_context_tokens=128_000,
        max_output_tokens=16_384,
        prompt_cost_per_million=2.50,
        completion_cost_per_million=10.00,
    ),
    "gpt-4o-mini": ModelBudget(
        model="gpt-4o-mini",
        max_context_tokens=128_000,
        max_output_tokens=16_384,
        prompt_cost_per_million=0.15,
        completion_cost_per_million=0.60,
    ),
    "o1": ModelBudget(
        model="o1",
        max_context_tokens=200_000,
        max_output_tokens=100_000,
        prompt_cost_per_million=15.00,
        completion_cost_per_million=60.00,
    ),
    "o1-mini": ModelBudget(
        model="o1-mini",
        max_context_tokens=128_000,
        max_output_tokens=65_536,
        prompt_cost_per_million=1.10,
        completion_cost_per_million=4.40,
    ),
    "gpt-4-turbo": ModelBudget(
        model="gpt-4-turbo",
        max_context_tokens=128_000,
        max_output_tokens=4_096,
        prompt_cost_per_million=10.00,
        completion_cost_per_million=30.00,
    ),
    "gpt-3.5-turbo": ModelBudget(
        model="gpt-3.5-turbo",
        max_context_tokens=16_385,
        max_output_tokens=4_096,
        prompt_cost_per_million=0.50,
        completion_cost_per_million=1.50,
    ),
    "claude-3-5-sonnet": ModelBudget(
        model="claude-3-5-sonnet",
        max_context_tokens=200_000,
        max_output_tokens=8_192,
        prompt_cost_per_million=3.00,
        completion_cost_per_million=15.00,
    ),
    "claude-3-opus": ModelBudget(
        model="claude-3-opus",
        max_context_tokens=200_000,
        max_output_tokens=4_096,
        prompt_cost_per_million=15.00,
        completion_cost_per_million=75.00,
    ),
    "claude-3-haiku": ModelBudget(
        model="claude-3-haiku",
        max_context_tokens=200_000,
        max_output_tokens=4_096,
        prompt_cost_per_million=0.25,
        completion_cost_per_million=1.25,
    ),
    "gemini-1.5-pro": ModelBudget(
        model="gemini-1.5-pro",
        max_context_tokens=2_097_152,
        max_output_tokens=8_192,
        prompt_cost_per_million=3.50,
        completion_cost_per_million=10.50,
    ),
    "gemini-1.5-flash": ModelBudget(
        model="gemini-1.5-flash",
        max_context_tokens=1_048_576,
        max_output_tokens=8_192,
        prompt_cost_per_million=0.075,
        completion_cost_per_million=0.30,
    ),
    "gemini-2.0-flash": ModelBudget(
        model="gemini-2.0-flash",
        max_context_tokens=1_048_576,
        max_output_tokens=8_192,
        prompt_cost_per_million=0.10,
        completion_cost_per_million=0.40,
    ),
    "llama-3.1-8b": ModelBudget(
        model="llama-3.1-8b",
        max_context_tokens=131_072,
        max_output_tokens=4_096,
        prompt_cost_per_million=0.0,
        completion_cost_per_million=0.0,
    ),
    "llama-3.1-70b": ModelBudget(
        model="llama-3.1-70b",
        max_context_tokens=131_072,
        max_output_tokens=4_096,
        prompt_cost_per_million=0.0,
        completion_cost_per_million=0.0,
    ),
    "llama-3.1-405b": ModelBudget(
        model="llama-3.1-405b",
        max_context_tokens=131_072,
        max_output_tokens=4_096,
        prompt_cost_per_million=0.0,
        completion_cost_per_million=0.0,
    ),
    "mistral-large": ModelBudget(
        model="mistral-large",
        max_context_tokens=128_000,
        max_output_tokens=8_192,
        prompt_cost_per_million=2.00,
        completion_cost_per_million=6.00,
    ),
}


def get_model_budget(model: str) -> ModelBudget:
    """Retrieve or synthesize a ModelBudget specification for an arbitrary model.

    Args:
        model: Model name or provider-qualified identifier (e.g. 'openai/gpt-4o').

    Returns:
        The matched or default ModelBudget instance.

    Notes/Architectural Intent:
        Strips provider prefixes and version timestamps to resolve matching budgets.
        Falls back to a standard conservative 128k context ceiling if unregistered.
    """
    clean_model = model.lower().split("/")[-1].strip()
    if clean_model in MODEL_BUDGET_CATALOG:
        return MODEL_BUDGET_CATALOG[clean_model]

    for key, budget in MODEL_BUDGET_CATALOG.items():
        if key in clean_model or clean_model in key:
            return budget

    return ModelBudget(
        model=model,
        max_context_tokens=128_000,
        max_output_tokens=4_096,
        prompt_cost_per_million=0.0,
        completion_cost_per_million=0.0,
    )


__all__ = [
    "ChatMessage",
    "get_model_budget",
    "MODEL_BUDGET_CATALOG",
    "ModelBudget",
    "PruneStrategy",
    "TokenUsage",
]
