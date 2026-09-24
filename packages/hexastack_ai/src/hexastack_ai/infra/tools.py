import inspect
from collections.abc import Sequence
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.models import Model
from pydantic_core import PydanticUndefined

from hexastack_core.domain import Command, Generic, Query
from hexastack_cqrs.infra.pipeline import ExecutionPipeline

__all__ = [
    "attach_mcp_registry",
    "create_cqrs_agent",
    "create_tool_for_message",
]


def attach_mcp_registry(
    agent: Agent[Any, Any],
    registry: Any,
    pipeline: ExecutionPipeline,
    read_only: bool = False,
) -> list[str]:
    """Discover tools from an MCP server registry and attach them in-process to a PydanticAI Agent.

    Notes/Architectural Intent:
        Enables zero-overhead, in-process tool binding for CQRS commands and queries
        registered via @mcp_tool without requiring loopback network IPC. Respects
        least-privilege invariants when read_only is enabled.

    Args:
        agent: Target PydanticAI Agent instance.
        registry: McpServerRegistry or object exposing a .tools metadata sequence.
        pipeline: Target ExecutionPipeline for in-process execution.
        read_only: When True, omits mutating commands and mounts only read-only queries.

    Returns:
        List of registered tool names.
    """
    tools = getattr(registry, "tools", [])
    registered_names: list[str] = []

    for tool_meta in tools:
        is_tool_read_only = getattr(tool_meta, "read_only", False)
        if read_only and not is_tool_read_only:
            continue

        target = getattr(tool_meta, "target", None)
        if inspect.isclass(target):
            tool_fn = create_tool_for_message(target, pipeline)
            agent.tool_plain(tool_fn)
            registered_names.append(getattr(tool_meta, "name", target.__name__))
        elif callable(target):
            agent.tool_plain(target)
            registered_names.append(
                getattr(tool_meta, "name", getattr(target, "__name__", "tool"))
            )

    return registered_names


def create_cqrs_agent(
    pipeline: ExecutionPipeline,
    messages: Sequence[type[Command | Query[Any]]] = (),
    model: str | Model = "test",
    system_prompt: str | None = None,
    registry: Any | None = None,
    read_only: bool = False,
) -> Agent[Any, Any]:
    """Assemble a PydanticAI Agent with CQRS message handlers reflected as tools.

    Notes/Architectural Intent:
        Bridges the CQRS message bus with AI agent capabilities. The agent can
        reason, select appropriate Commands/Queries, and invoke domain logic
        through the standard Hexastack execution pipeline. Automatically binds
        tools from a local McpServerRegistry when provided.

    Args:
        pipeline: Target ExecutionPipeline.
        messages: Optional sequence of Command/Query classes to expose as tools.
        model: Target model string ('test', 'openai:gpt-4o', etc.) or Model instance.
        system_prompt: Optional initial persona instructions.
        registry: Optional McpServerRegistry to auto-discover @mcp_tool definitions.
        read_only: When True, restricts auto-attached registry tools to queries only.

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

    if registry is not None:
        attach_mcp_registry(
            agent=agent,
            registry=registry,
            pipeline=pipeline,
            read_only=read_only,
        )

    return agent


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
