import inspect
from collections.abc import Callable
from typing import Any

from mcp.client.session import ClientSession
from mcp.types import CallToolResult, TextContent, Tool
from pydantic_ai import Agent

__all__ = [
    "attach_external_mcp_tools",
    "create_mcp_client_tool",
]

_JSON_SCHEMA_TYPE_MAP: dict[str, type[Any]] = {
    "array": list,
    "boolean": bool,
    "integer": int,
    "number": float,
    "object": dict,
    "string": str,
}


def _map_json_schema_type(type_name: str | None) -> type[Any]:
    if not type_name:
        return Any
    return _JSON_SCHEMA_TYPE_MAP.get(type_name.lower(), Any)


def _format_tool_result(result: CallToolResult | Any) -> Any:
    """Format and unpack CallToolResult payload into text or structured data."""
    if not (hasattr(result, "content") and result.content):
        return getattr(result, "text", str(result))

    texts: list[str] = [c.text for c in result.content if isinstance(c, TextContent)]
    if len(texts) == 1:
        return texts[0]
    if texts:
        return "\n".join(texts)
    return [
        c.model_dump() if hasattr(c, "model_dump") else str(c) for c in result.content
    ]


def _extract_schema_parameters(
    schema: dict[str, Any],
) -> tuple[list[inspect.Parameter], dict[str, Any]]:
    """Derive inspect.Parameter list and annotations from tool inputSchema."""
    props: dict[str, Any] = schema.get("properties", {})
    required: set[str] = set(schema.get("required", []))

    parameters: list[inspect.Parameter] = []
    annotations: dict[str, Any] = {}

    for param_name, param_info in props.items():
        type_str = param_info.get("type") if isinstance(param_info, dict) else None
        param_type = _map_json_schema_type(type_str)
        default_val = inspect.Parameter.empty if param_name in required else None

        parameters.append(
            inspect.Parameter(
                name=param_name,
                kind=inspect.Parameter.KEYWORD_ONLY,
                annotation=param_type,
                default=default_val,
            )
        )
        annotations[param_name] = param_type

    annotations["return"] = Any
    return parameters, annotations


def create_mcp_client_tool(
    session: ClientSession,
    tool: Tool,
) -> Callable[..., Any]:
    """Synthesize a dynamically typed callable tool from an MCP Tool definition.

    Notes/Architectural Intent:
        Derives parameter annotations and keyword-only signatures from the remote
        tool's JSON schema inputSchema, enabling PydanticAI to generate accurate
        function-calling specifications while routing execution over the active
        MCP ClientSession.

    Args:
        session: Active ClientSession connected to an MCP server.
        tool: MCP Tool metadata including name, description, and inputSchema.

    Returns:
        Async callable compatible with PydanticAI agent.tool_plain().
    """
    schema = tool.inputSchema or {}
    parameters, annotations = _extract_schema_parameters(schema)

    async def mcp_tool_executor(**kwargs: Any) -> Any:
        result = await session.call_tool(tool.name, arguments=kwargs)
        return _format_tool_result(result)

    setattr(  # noqa: B010
        mcp_tool_executor,
        "__signature__",
        inspect.Signature(parameters=parameters),
    )
    mcp_tool_executor.__annotations__ = annotations
    mcp_tool_executor.__name__ = tool.name
    mcp_tool_executor.__doc__ = tool.description or f"External MCP tool '{tool.name}'."
    return mcp_tool_executor


async def attach_external_mcp_tools(
    agent: Agent[Any, Any],
    session: ClientSession,
) -> list[str]:
    """Query external MCP server tools and register them dynamically onto a PydanticAI Agent.

    Notes/Architectural Intent:
        Empowers Hexastack AI agents to consume arbitrary external MCP servers
        (e.g., Filesystem, SQLite, Playwright, or remote microservices) alongside
        internal CQRS domain tools.

    Args:
        agent: Target PydanticAI Agent instance.
        session: Active ClientSession connected to an MCP server.

    Returns:
        List of registered tool names.
    """
    tools_response = await session.list_tools()
    registered_names: list[str] = []

    for tool in tools_response.tools:
        tool_fn = create_mcp_client_tool(session, tool)
        agent.tool_plain(tool_fn)
        registered_names.append(tool.name)

    return registered_names
