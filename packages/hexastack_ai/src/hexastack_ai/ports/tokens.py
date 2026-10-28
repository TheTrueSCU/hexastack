"""Abstract port interface for token counting, budget sizing, and context window pruning.

Notes/Architectural Intent:
    Defines the contract for tokenization engines. Isolates application and domain
    logic from concrete tokenization libraries like tiktoken or HuggingFace tokenizers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from hexastack_ai.domain.tokens import ChatMessage, PruneStrategy


class TokenizerPort(ABC):
    """Abstract interface defining token counting, budget evaluation, and message pruning.

    Notes/Architectural Intent:
        Enables interchangeable offline and online tokenization strategies across
        diverse model families (OpenAI, Anthropic, Gemini, Llama).
    """

    @abstractmethod
    def count_tokens(self, text: str, model: str | None = None) -> int:
        """Calculate the number of tokens in a plain text string.

        Args:
            text: Input string to tokenize.
            model: Optional model identifier to select tokenizer encoding.

        Returns:
            Total token count.

        Raises:
            TokenizerNotFoundError: If no matching tokenizer or encoding can be resolved.
        """

    @abstractmethod
    def count_messages_tokens(
        self,
        messages: Sequence[ChatMessage | dict[str, Any]],
        model: str | None = None,
    ) -> int:
        """Calculate total tokens consumed by a series of chat turns including message framing overhead.

        Args:
            messages: Sequence of chat messages or raw message dictionaries.
            model: Optional model identifier.

        Returns:
            Aggregate token count including role tags and framing delimiters.

        Raises:
            TokenizerNotFoundError: If no matching tokenizer can be resolved.
        """

    @abstractmethod
    def prune_messages(
        self,
        messages: Sequence[ChatMessage | dict[str, Any]],
        max_tokens: int,
        model: str | None = None,
        strategy: PruneStrategy = "oldest_first",
        preserve_system: bool = True,
    ) -> list[ChatMessage]:
        """Prune conversational history to fit within a maximum token limit.

        Args:
            messages: Sequence of chat messages to evaluate and prune.
            max_tokens: Upper ceiling on total tokens permitted.
            model: Optional model identifier used to calculate message lengths.
            strategy: Pruning algorithm ("oldest_first", "keep_system_and_last_n", "trim_token_exact").
            preserve_system: Whether system prompts must be retained intact.

        Returns:
            Pruned list of ChatMessage instances fitting within max_tokens.

        Raises:
            TokenLimitExceededError: If system messages alone exceed max_tokens.
            TokenizerNotFoundError: If no tokenizer can be resolved.
        """

    @abstractmethod
    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ) -> float:
        """Estimate the operational cost in USD for the given token volume and model.

        Args:
            prompt_tokens: Number of prompt/input tokens.
            completion_tokens: Number of completion/output tokens.
            model: Model identifier.

        Returns:
            Estimated total cost in USD.
        """


__all__ = [
    "TokenizerPort",
]
