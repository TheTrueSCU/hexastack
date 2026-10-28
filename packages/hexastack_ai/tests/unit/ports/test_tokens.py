from collections.abc import Sequence
from typing import Any

from hexastack_ai.domain.tokens import ChatMessage, PruneStrategy
from hexastack_ai.ports.tokens import TokenizerPort


class DummyTokenizer(TokenizerPort):
    def count_tokens(self, text: str, model: str | None = None) -> int:
        return len(text.split()) if text else 0

    def count_messages_tokens(
        self,
        messages: Sequence[ChatMessage | dict[str, Any]],
        model: str | None = None,
    ) -> int:
        return sum(
            len(str(m.get("content", "") if isinstance(m, dict) else m.content).split())
            for m in messages
        )

    def prune_messages(
        self,
        messages: Sequence[ChatMessage | dict[str, Any]],
        max_tokens: int,
        model: str | None = None,
        strategy: PruneStrategy = "oldest_first",
        preserve_system: bool = True,
    ) -> list[ChatMessage]:
        res = [
            m
            if isinstance(m, ChatMessage)
            else ChatMessage(role=m["role"], content=m["content"])
            for m in messages
        ]
        return res[:max_tokens]

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ) -> float:
        return (prompt_tokens + completion_tokens) * 0.00001


def test_tokenizer_port_dummy_implementation():
    tokenizer = DummyTokenizer()
    count = tokenizer.count_tokens("one two three")
    assert count == 3

    msg_count = tokenizer.count_messages_tokens(
        [
            ChatMessage(role="user", content="hello world"),
            ChatMessage(role="assistant", content="hi there"),
        ]
    )
    assert msg_count == 4

    pruned = tokenizer.prune_messages(
        [
            ChatMessage(role="user", content="first"),
            ChatMessage(role="user", content="second"),
        ],
        max_tokens=1,
    )
    assert len(pruned) == 1
    assert pruned[0].content == "first"

    cost = tokenizer.estimate_cost(100, 100, "any-model")
    assert round(cost, 5) == 0.002
