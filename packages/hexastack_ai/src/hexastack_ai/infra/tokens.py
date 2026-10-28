"""Infra coordinator managing token budgets, context window sizing, and usage telemetry.

Notes/Architectural Intent:
    Orchestrates TokenizerPort and TokenTelemetryHook into a unified manager
    that enforces model context window boundaries, executes pre-call prompt pruning,
    and logs token expenditures across LLM invocations.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from hexastack_ai.adapters.tokens import LocalTokenizerAdapter, TokenTelemetryHook
from hexastack_ai.domain.tokens import (
    ChatMessage,
    ModelBudget,
    PruneStrategy,
    TokenUsage,
    get_model_budget,
)
from hexastack_ai.ports.tokens import TokenizerPort

if TYPE_CHECKING:
    from hexastack_core.ports.logging import LoggingPort


class TokenBudgetManager:
    """Coordinates local token counting, context budgeting, and telemetry emission.

    Notes/Architectural Intent:
        Sits between application orchestration and LLM adapter dispatch to guarantee
        that prompts fit within model context windows and expenses are tracked.
    """

    def __init__(
        self,
        tokenizer: TokenizerPort | None = None,
        telemetry_hook: TokenTelemetryHook | None = None,
        logger: LoggingPort | None = None,
        enable_otel: bool = True,
    ) -> None:
        """Initialize TokenBudgetManager with tokenizer and telemetry services.

        Args:
            tokenizer: TokenizerPort implementation (defaults to LocalTokenizerAdapter).
            telemetry_hook: Optional pre-configured TokenTelemetryHook.
            logger: Optional LoggingPort for structured audit logs.
            enable_otel: Whether to emit OpenTelemetry metrics.
        """
        self.tokenizer = tokenizer or LocalTokenizerAdapter()
        self.telemetry_hook = telemetry_hook or TokenTelemetryHook(
            logger=logger,
            enable_otel=enable_otel,
        )

    def get_budget(self, model: str) -> ModelBudget:
        """Retrieve the ModelBudget specification for the requested model.

        Args:
            model: Model identifier.

        Returns:
            ModelBudget instance.
        """
        return get_model_budget(model)

    def calculate_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ) -> TokenUsage:
        """Calculate TokenUsage including estimated USD expense.

        Args:
            prompt_tokens: Number of prompt tokens.
            completion_tokens: Number of completion tokens.
            model: Model identifier.

        Returns:
            TokenUsage value object.
        """
        total = prompt_tokens + completion_tokens
        cost = self.tokenizer.estimate_cost(prompt_tokens, completion_tokens, model)
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            estimated_cost_usd=cost,
        )

    def prepare_messages(
        self,
        messages: Sequence[ChatMessage | dict[str, Any]],
        model: str,
        max_context_tokens: int | None = None,
        reserved_output_tokens: int = 1024,
        strategy: PruneStrategy = "oldest_first",
        preserve_system: bool = True,
    ) -> tuple[list[ChatMessage], TokenUsage]:
        """Prune messages to fit within model context limits and return baseline usage.

        Args:
            messages: Sequence of chat turns.
            model: Target model identifier.
            max_context_tokens: Optional explicit maximum context ceiling.
            reserved_output_tokens: Expected completion tokens to reserve from ceiling.
            strategy: Pruning strategy to apply if context budget is exceeded.
            preserve_system: Whether system prompts must be retained.

        Returns:
            Tuple of (pruned_messages, TokenUsage).
        """
        budget = self.get_budget(model)
        ceiling = max_context_tokens or budget.available_context_tokens(
            reserved_output_tokens
        )

        pruned = self.tokenizer.prune_messages(
            messages=messages,
            max_tokens=ceiling,
            model=model,
            strategy=strategy,
            preserve_system=preserve_system,
        )
        prompt_tokens = self.tokenizer.count_messages_tokens(pruned, model=model)
        usage = self.calculate_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            model=model,
        )
        return pruned, usage

    def record_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
        attributes: dict[str, Any] | None = None,
    ) -> TokenUsage:
        """Compute costs, record telemetry, and return final TokenUsage.

        Args:
            prompt_tokens: Prompt tokens processed.
            completion_tokens: Completion tokens generated.
            model: Model identifier.
            attributes: Optional metadata attributes for telemetry tagging.

        Returns:
            TokenUsage instance capturing total tokens and estimated cost.
        """
        usage = self.calculate_usage(prompt_tokens, completion_tokens, model)
        self.telemetry_hook.record_usage(usage, model, attributes=attributes)
        return usage


__all__ = [
    "TokenBudgetManager",
]
