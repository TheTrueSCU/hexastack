from typing import Any

from pydantic_ai import Agent

from hexastack_ai.domain.exceptions import AgentExecutionError


class PydanticAiAgentAdapter:
    """Adapter wrapping a PydanticAI Agent instance.

    Notes/Architectural Intent:
        Encapsulates agent execution lifecycle, converting low-level exceptions
        into Hexastack domain AgentExecutionError.
    """

    def __init__(self, agent: Agent[Any, Any]) -> None:
        """Initialize adapter with a configured PydanticAI Agent instance."""
        self._agent = agent

    @property
    def agent(self) -> Agent[Any, Any]:
        """Access the underlying PydanticAI Agent instance."""
        return self._agent

    async def run(self, prompt: str, **kwargs: Any) -> Any:
        """Asynchronously run the agent against a user prompt.

        Args:
            prompt: User request prompt.
            **kwargs: Extra parameters passed to agent.run().

        Returns:
            The agent result data.

        Raises:
            AgentExecutionError: If agent execution or tool call fails.
        """
        try:
            result = await self._agent.run(prompt, **kwargs)
            return getattr(result, "output", getattr(result, "data", result))
        except Exception as exc:
            raise AgentExecutionError(str(exc)) from exc

    def run_sync(self, prompt: str, **kwargs: Any) -> Any:
        """Synchronously run the agent against a user prompt.

        Args:
            prompt: User request prompt.
            **kwargs: Extra parameters passed to agent.run_sync().

        Returns:
            The agent result data.

        Raises:
            AgentExecutionError: If agent execution fails.
        """
        try:
            result = self._agent.run_sync(prompt, **kwargs)
            return getattr(result, "output", getattr(result, "data", result))
        except Exception as exc:
            raise AgentExecutionError(str(exc)) from exc


__all__ = [
    "PydanticAiAgentAdapter",
]
