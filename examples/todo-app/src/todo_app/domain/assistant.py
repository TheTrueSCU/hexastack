"""Autonomous AI Productivity Assistant service built on LlmProviderPort."""

from __future__ import annotations

from hexastack_core.ports.ai import LlmProviderPort
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from todo_app.domain.commands import ListTodosQuery


class TodoAiAssistant:
    """Intelligent productivity assistant interacting with domain CQRS pipeline.

    Notes/Architectural Intent:
        Demonstrates agent-native domain workflows without coupling to specific LLM models.
    """

    def __init__(self, llm: LlmProviderPort, pipeline: ExecutionPipeline) -> None:
        self.llm = llm
        self.pipeline = pipeline

    def generate_morning_briefing(self, user_id: str = "alice") -> str:
        """Query pending tasks for user and generate prioritized executive morning summary."""
        todos = self.pipeline.execute(ListTodosQuery(owner_id=user_id, completed_only=False))
        if not todos:
            return "Good morning! You have no pending tasks today. Enjoy your day!"

        task_lines = [f"- [{t.priority.value.upper()}] {t.title}: {t.description}" for t in todos]
        prompt = (
            f"You are an executive productivity assistant. Review these {len(todos)} pending tasks "
            f"for user '{user_id}' and provide an action plan with top priorities:\n"
            + "\n".join(task_lines)
        )
        return self.llm.generate_text(prompt, system_prompt="You are a crisp, high-signal AI executive assistant.")


__all__ = [
    "TodoAiAssistant",
]
