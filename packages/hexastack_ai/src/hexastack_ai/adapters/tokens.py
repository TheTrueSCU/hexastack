"""Concrete tokenizer adapter and telemetry hook for local token counting and context budgeting.

Notes/Architectural Intent:
    Implements TokenizerPort with local, offline token counting via tiktoken and
    HuggingFace tokenizers. Provides OpenTelemetry metrics and structured logging
    telemetry hooks to monitor token expenditure without vendor lock-in.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import tiktoken

from hexastack_ai.domain.exceptions import (
    TokenizerNotFoundError,
    TokenLimitExceededError,
)
from hexastack_ai.domain.tokens import (
    ChatMessage,
    PruneStrategy,
    TokenUsage,
    get_model_budget,
)
from hexastack_ai.ports.tokens import TokenizerPort

if TYPE_CHECKING:
    from pathlib import Path

    from hexastack_core.ports.logging import LoggingPort

_LOGGER = logging.getLogger(__name__)

# Calibrated offline token density multipliers relative to OpenAI cl100k/o200k
_PROVIDER_CALIBRATION: dict[str, float] = {
    "anthropic": 1.12,
    "claude": 1.12,
    "gemini": 1.08,
    "google": 1.08,
    "llama": 1.05,
    "meta": 1.05,
    "mistral": 1.05,
}


def _normalize_message(msg: ChatMessage | dict[str, Any]) -> ChatMessage:
    """Normalize input message dictionary or entity to ChatMessage.

    Args:
        msg: ChatMessage or dictionary with role and content keys.

    Returns:
        Standardized ChatMessage instance.
    """
    if isinstance(msg, ChatMessage):
        return msg
    return ChatMessage(
        role=str(msg.get("role", "user")),
        content=str(msg.get("content", "")),
        name=msg.get("name"),
        metadata=msg.get("metadata", {}),
    )


class LocalTokenizerAdapter(TokenizerPort):
    """Local, offline token counting engine leveraging tiktoken and tokenizers.

    Notes/Architectural Intent:
        Calculates exact token budgets locally without making external network calls.
        Supports OpenAI, Anthropic, Gemini, and Llama token estimates via calibrated
        BPE models and custom HuggingFace tokenizers.
    """

    def __init__(
        self,
        default_model: str = "gpt-4o",
        custom_tokenizer: Any | None = None,
        tokenizer_path: str | Path | None = None,
    ) -> None:
        """Initialize LocalTokenizerAdapter with optional pre-configured tokenizer.

        Args:
            default_model: Default model identifier when none is provided in calls.
            custom_tokenizer: Pre-initialized HuggingFace or custom Tokenizer instance.
            tokenizer_path: Filesystem path to a HuggingFace tokenizer.json file.
        """
        self.default_model = default_model
        self._tiktoken_cache: dict[str, tiktoken.Encoding] = {}
        self._custom_tokenizer = custom_tokenizer

        if tokenizer_path is not None and self._custom_tokenizer is None:
            from tokenizers import Tokenizer

            self._custom_tokenizer = Tokenizer.from_file(str(tokenizer_path))

    def _resolve_encoding(self, model: str | None) -> tuple[tiktoken.Encoding, float]:
        """Resolve tiktoken encoding and calibration multiplier for target model.

        Args:
            model: Optional model identifier.

        Returns:
            Tuple of (tiktoken.Encoding, calibration_factor).

        Raises:
            TokenizerNotFoundError: If encoding resolution fails completely.
        """
        target_model = (model or self.default_model).lower().strip()
        clean_model = target_model.split("/")[-1].strip()

        multiplier = 1.0
        for provider, factor in _PROVIDER_CALIBRATION.items():
            if provider in target_model:
                multiplier = factor
                break

        if clean_model in self._tiktoken_cache:
            return self._tiktoken_cache[clean_model], multiplier

        try:
            encoding = tiktoken.encoding_for_model(clean_model)
            self._tiktoken_cache[clean_model] = encoding
            return encoding, multiplier
        except KeyError:
            pass

        fallback_encoding_name = (
            "o200k_base"
            if "o1" in clean_model or "4o" in clean_model
            else "cl100k_base"
        )
        try:
            encoding = tiktoken.get_encoding(fallback_encoding_name)
            self._tiktoken_cache[clean_model] = encoding
            return encoding, multiplier
        except Exception as exc:
            msg = f"Failed to resolve tokenizer for model '{target_model}'"
            raise TokenizerNotFoundError(msg) from exc

    def count_tokens(self, text: str, model: str | None = None) -> int:
        """Calculate token count for plain text.

        Args:
            text: Input string.
            model: Optional model identifier.

        Returns:
            Number of tokens.
        """
        if not text:
            return 0

        if self._custom_tokenizer is not None:
            encoding = self._custom_tokenizer.encode(text)
            return len(encoding.ids)

        encoding, multiplier = self._resolve_encoding(model)
        raw_tokens = len(encoding.encode(text, disallowed_special=()))
        if multiplier != 1.0:
            return max(1, int(round(raw_tokens * multiplier)))
        return raw_tokens

    def count_messages_tokens(
        self,
        messages: Sequence[ChatMessage | dict[str, Any]],
        model: str | None = None,
    ) -> int:
        """Calculate total tokens consumed by chat turns including ChatML framing overhead.

        Args:
            messages: List of chat messages or dictionaries.
            model: Optional model identifier.

        Returns:
            Total token count including message delimiters.
        """
        if not messages:
            return 0

        tokens = 0
        for raw_msg in messages:
            msg = _normalize_message(raw_msg)
            # Standard ChatML framing: 3 tokens per message for <|im_start|>{role}\n{content}<|im_end|>\n
            tokens += 3
            tokens += self.count_tokens(msg.role, model=model)
            tokens += self.count_tokens(msg.content, model=model)
            if msg.name is not None:
                tokens += 1 + self.count_tokens(msg.name, model=model)

        # 3 tokens for assistant priming: <|im_start|>assistant\n
        tokens += 3
        return tokens

    def prune_messages(
        self,
        messages: Sequence[ChatMessage | dict[str, Any]],
        max_tokens: int,
        model: str | None = None,
        strategy: PruneStrategy = "oldest_first",
        preserve_system: bool = True,
    ) -> list[ChatMessage]:
        """Prune conversational history to fit strictly within max_tokens.

        Args:
            messages: Sequence of chat turns.
            max_tokens: Maximum allowed token budget.
            model: Optional model identifier.
            strategy: Algorithm to use ("oldest_first", "keep_system_and_last_n", "trim_token_exact").
            preserve_system: Whether system prompts must be protected from pruning.

        Returns:
            Pruned list of ChatMessage instances.

        Raises:
            TokenLimitExceededError: If system messages alone exceed max_tokens.
        """
        normalized = [_normalize_message(m) for m in messages]
        if not normalized:
            return []

        current_tokens = self.count_messages_tokens(normalized, model=model)
        if current_tokens <= max_tokens:
            return normalized

        if preserve_system:
            system_msgs = [m for m in normalized if m.role == "system"]
            conversation = [m for m in normalized if m.role != "system"]
        else:
            system_msgs = []
            conversation = list(normalized)

        sys_tokens = (
            self.count_messages_tokens(system_msgs, model=model) if system_msgs else 3
        )
        if sys_tokens > max_tokens:
            msg = f"System messages consume {sys_tokens} tokens, exceeding max_tokens={max_tokens}"
            raise TokenLimitExceededError(
                message=msg,
                current_tokens=sys_tokens,
                max_tokens=max_tokens,
                model=model,
            )

        if strategy == "trim_token_exact":
            return self._prune_trim_exact(system_msgs, conversation, max_tokens, model)
        if strategy == "keep_system_and_last_n":
            return self._prune_keep_last_n(system_msgs, conversation, max_tokens, model)
        return self._prune_oldest_first(system_msgs, conversation, max_tokens, model)

    def _prune_oldest_first(
        self,
        system_msgs: list[ChatMessage],
        conversation: list[ChatMessage],
        max_tokens: int,
        model: str | None,
    ) -> list[ChatMessage]:
        """Drop oldest non-system messages until total tokens <= max_tokens."""
        working = list(conversation)
        while working:
            candidate = system_msgs + working
            if self.count_messages_tokens(candidate, model=model) <= max_tokens:
                return candidate
            working.pop(0)

        return list(system_msgs)

    def _prune_keep_last_n(
        self,
        system_msgs: list[ChatMessage],
        conversation: list[ChatMessage],
        max_tokens: int,
        model: str | None,
    ) -> list[ChatMessage]:
        """Keep last N conversation turns that fit within max_tokens."""
        for count in range(len(conversation), 0, -1):
            candidate = system_msgs + conversation[-count:]
            if self.count_messages_tokens(candidate, model=model) <= max_tokens:
                return candidate

        return list(system_msgs)

    def _prune_trim_exact(
        self,
        system_msgs: list[ChatMessage],
        conversation: list[ChatMessage],
        max_tokens: int,
        model: str | None,
    ) -> list[ChatMessage]:
        """Trim the earliest eligible message to exactly fit the remaining token budget."""
        if not conversation:
            return list(system_msgs)

        candidate = system_msgs + conversation
        if self.count_messages_tokens(candidate, model=model) <= max_tokens:
            return candidate

        # Find how many suffix messages fit intact
        suffix_msgs: list[ChatMessage] = []
        for msg in reversed(conversation):
            test_candidate = system_msgs + [msg] + suffix_msgs
            if self.count_messages_tokens(test_candidate, model=model) <= max_tokens:
                suffix_msgs.insert(0, msg)
            else:
                break

        remaining_count = len(conversation) - len(suffix_msgs)
        if remaining_count == 0:
            return system_msgs + suffix_msgs

        oldest_to_trim = conversation[remaining_count - 1]
        tokens_used = self.count_messages_tokens(system_msgs + suffix_msgs, model=model)
        allowance = max(0, max_tokens - tokens_used - 4)  # 4 tokens for message framing

        if allowance > 5:
            words = oldest_to_trim.content.split()
            low = 1
            high = len(words)
            best_text = ""

            while low <= high:
                mid = (low + high) // 2
                partial_text = " ".join(words[:mid]) + "..."
                partial_msg = ChatMessage(
                    role=oldest_to_trim.role,
                    content=partial_text,
                    name=oldest_to_trim.name,
                )
                if (
                    self.count_messages_tokens(
                        system_msgs + [partial_msg] + suffix_msgs, model=model
                    )
                    <= max_tokens
                ):
                    best_text = partial_text
                    low = mid + 1
                else:
                    high = mid - 1

            if best_text:
                trimmed_msg = ChatMessage(
                    role=oldest_to_trim.role,
                    content=best_text,
                    name=oldest_to_trim.name,
                )
                return system_msgs + [trimmed_msg] + suffix_msgs

        return system_msgs + suffix_msgs

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ) -> float:
        """Estimate cost in USD using model budget rates.

        Args:
            prompt_tokens: Number of prompt tokens.
            completion_tokens: Number of completion tokens.
            model: Target model name.

        Returns:
            Estimated total cost in USD.
        """
        budget = get_model_budget(model)
        return budget.calculate_cost(prompt_tokens, completion_tokens)


class TokenTelemetryHook:
    """Telemetry recorder for LLM token usage and cost tracking via OpenTelemetry and LoggingPort.

    Notes/Architectural Intent:
        Emits standard OpenTelemetry metrics (llm.tokens.prompt, llm.tokens.completion,
        llm.tokens.total, llm.cost.usd) and writes structured audit logs via LoggingPort.
    """

    def __init__(
        self,
        logger: LoggingPort | None = None,
        enable_otel: bool = True,
    ) -> None:
        """Initialize TokenTelemetryHook.

        Args:
            logger: Optional LoggingPort instance for structured application logging.
            enable_otel: Whether to register and emit OpenTelemetry counters.
        """
        self._logger = logger
        self._enable_otel = enable_otel
        self._prompt_counter: Any | None = None
        self._completion_counter: Any | None = None
        self._total_counter: Any | None = None
        self._cost_counter: Any | None = None

        if self._enable_otel:
            self._init_otel_metrics()

    def _init_otel_metrics(self) -> None:
        """Initialize OpenTelemetry counters if opentelemetry is available."""
        try:
            from opentelemetry import metrics

            meter = metrics.get_meter("hexastack.ai.tokens")
            self._prompt_counter = meter.create_counter(
                "llm.tokens.prompt",
                unit="tokens",
                description="Number of prompt tokens submitted to LLM endpoints",
            )
            self._completion_counter = meter.create_counter(
                "llm.tokens.completion",
                unit="tokens",
                description="Number of completion tokens generated by LLM endpoints",
            )
            self._total_counter = meter.create_counter(
                "llm.tokens.total",
                unit="tokens",
                description="Aggregate count of all LLM tokens processed",
            )
            self._cost_counter = meter.create_counter(
                "llm.cost.usd",
                unit="USD",
                description="Estimated cost of LLM inference in USD",
            )
        except Exception:
            _LOGGER.debug(
                "OpenTelemetry metrics not initialized for TokenTelemetryHook"
            )

    def record_usage(
        self,
        usage: TokenUsage,
        model: str,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Record token counts and cost into OpenTelemetry metrics and structured logs.

        Args:
            usage: TokenUsage value object containing token counts and cost.
            model: Model identifier.
            attributes: Additional metric dimension tags and log attributes.
        """
        attrs = {"model": model, **(attributes or {})}

        if self._enable_otel:
            if self._prompt_counter is not None and usage.prompt_tokens > 0:
                self._prompt_counter.add(usage.prompt_tokens, attributes=attrs)
            if self._completion_counter is not None and usage.completion_tokens > 0:
                self._completion_counter.add(usage.completion_tokens, attributes=attrs)
            if self._total_counter is not None and usage.total_tokens > 0:
                self._total_counter.add(usage.total_tokens, attributes=attrs)
            if (
                self._cost_counter is not None
                and usage.estimated_cost_usd is not None
                and usage.estimated_cost_usd > 0.0
            ):
                self._cost_counter.add(usage.estimated_cost_usd, attributes=attrs)

        if self._logger is not None:
            log_data: dict[str, Any] = {
                "model": model,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "estimated_cost_usd": usage.estimated_cost_usd,
                **(attributes or {}),
            }
            self._logger.info("LLM token usage recorded", extra=log_data)


__all__ = [
    "LocalTokenizerAdapter",
    "TokenTelemetryHook",
]
