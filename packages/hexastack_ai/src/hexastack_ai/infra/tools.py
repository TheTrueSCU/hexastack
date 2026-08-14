import inspect
from collections.abc import Sequence
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_core import PydanticUndefined

from hexastack_core.domain import Command, Generic, Query
from hexastack_cqrs.infra.pipeline import ExecutionPipeline


def create_tool_for_message(
    msg_cls: type[Generic],
    pipeline: ExecutionPipeline,
) -> Any:
    """Create a typed tool function that constructs a CQRS message and executes it.

    Notes/Architectural Intent:
        Reflects Pydantic model fields dynamically onto the generated tool function's
        `__signature__` and `__annotations__`. This allows PydanticAI to generate
        accurate function-calling schemas while dispatching directly through
        the Hexastack ExecutionPipeline.

    Args:
        msg_cls: Domain Generic, Command, or Query class.
        pipeline: Target ExecutionPipeline instance.

    Returns:
        Callable tool function with dynamic signature and execution dispatcher.
    """

    async def tool_executor(**kwargs: Any) -> Any:
        msg = msg_cls.model_validate(kwargs)
        result = pipeline.execute(msg)
        if inspect.isawaitable(result):
            return await result
        return result

    # Reflect Pydantic model fields into parameter signature and annotations
    parameters = [
        inspect.Parameter(
            name=field_name,
            kind=inspect.Parameter.KEYWORD_ONLY,
            annotation=field_info.annotation or Any,
            default=(
                field_info.default
                if field_info.default is not PydanticUndefined
                else inspect.Parameter.empty
            ),
        )
        for field_name, field_info in msg_cls.model_fields.items()
    ]
    setattr(  # noqa: B010
        tool_executor,
        "__signature__",
        inspect.Signature(parameters=parameters),
    )
    setattr(  # noqa: B010
        tool_executor,
        "__annotations__",
        {
            name: field_info.annotation or Any
            for name, field_info in msg_cls.model_fields.items()
        },
    )
    tool_executor.__name__ = msg_cls.__name__
    tool_executor.__doc__ = (
        msg_cls.__doc__ or f"Execute the {msg_cls.__name__} domain operation."
    )
    return tool_executor


def create_cqrs_agent(
    pipeline: ExecutionPipeline,
    messages: Sequence[type[Command | Query[Any]]],
    model: str | Model = "test",
    system_prompt: str | None = None,
) -> Agent[Any, Any]:
    """Assemble a PydanticAI Agent with CQRS message handlers reflected as tools.

    Notes/Architectural Intent:
        Bridges the CQRS message bus with AI agent capabilities. The agent can
        reason, select appropriate Commands/Queries, and invoke domain logic
        through the standard Hexastack execution pipeline.

    Args:
        pipeline: Target ExecutionPipeline.
        messages: Sequence of Command/Query classes to expose as tools.
        model: Target model string ('test', 'openai:gpt-4o', 'anthropic:claude-3-5-sonnet') or Model instance.
        system_prompt: Optional initial persona instructions.

    Returns:
        Configured PydanticAI Agent instance.
    """
    sys_prompt = system_prompt or (
        "You are an AI assistant capable of executing domain operations "
        "using the provided tools."
    )
    agent: Agent[Any, Any] = Agent(model=model, system_prompt=sys_prompt)

    for msg_cls in messages:
        tool_fn = create_tool_for_message(msg_cls, pipeline)
        agent.tool_plain(tool_fn)

    return agent


__all__ = [
    "create_cqrs_agent",
    "create_tool_for_message",
]
