"""Property-based tests for MCP tool registration and schema reflection.

Notes/Architectural Intent:
    Verifies invariants of dynamic Pydantic model reflection into FastMCP tool
    wrappers, ensuring strict parameter validation, read-only enforcement,
    and robust error containment across arbitrary input variations.
"""

from dataclasses import dataclass
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel, Field
from rodi import Container

from hexastack_core.domain.command import Command
from hexastack_cqrs.ports.buses import CommandBusPort
from hexastack_mcp.domain.exceptions import (
    ToolExecutionError,
    ToolUnauthorizedError,
    ToolValidationError,
)
from hexastack_mcp.infra.registries.server import McpServerRegistry


class DummyCommandBus(CommandBusPort):
    """Stub command bus recording dispatched instances."""

    def __init__(self) -> None:
        self.dispatched: list[Any] = []

    def dispatch(self, command: Any) -> Any:
        self.dispatched.append(command)
        return {"status": "success", "echo": getattr(command, "name", "unknown")}


class ErrorCommandBus(CommandBusPort):
    """Stub command bus raising an unhandled exception."""

    def dispatch(self, command: Any) -> Any:
        raise RuntimeError("Fatal database connection drop")


@dataclass(frozen=True)
class GeneratedCommand(Command):
    """Dynamically evaluated command dataclass."""

    name: str
    count: int = 1
    flag: bool = False


class GeneratedPydanticCommand(BaseModel):
    """Pydantic model command with validation constraints."""

    username: str = Field(min_length=2, max_length=50)
    score: int = Field(ge=0, le=1000)
    tag: str = "default"


@given(
    name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip() != ""),
    count=st.integers(min_value=-10000, max_value=10000),
    flag=st.booleans(),
)
@settings(max_examples=50)
@pytest.mark.asyncio
async def test_tool_wrapper_executes_valid_parameters(
    name: str, count: int, flag: bool
) -> None:
    """Property test verifying tool wrapper accepts and dispatches valid parameters.

    Args:
        name: Generated string parameter.
        count: Generated integer parameter.
        flag: Generated boolean parameter.

    Notes/Architectural Intent:
        Asserts that any valid permutation of declared model parameters executes
        successfully through the CQRS bus without schema mismatch.
    """
    container = Container()
    bus = DummyCommandBus()
    container.add_instance(bus, declared_class=CommandBusPort)

    registry = McpServerRegistry()
    wrapper = registry._create_cqrs_tool_wrapper(
        target_cls=GeneratedCommand,
        kind="command",
        container=container,
        read_only_tool=False,
        server_read_only=False,
    )

    result = await wrapper(name=name, count=count, flag=flag)
    assert result == {"status": "success", "echo": name}

    dispatched_count = len(bus.dispatched)
    assert dispatched_count == 1

    cmd = bus.dispatched[0]
    assert cmd.name == name
    assert cmd.count == count
    assert cmd.flag == flag


@given(
    bad_key=st.from_regex(r"[a-z][a-z0-9_]{1,15}", fullmatch=True).filter(
        lambda k: k not in {"name", "count", "flag"}
    ),
    bad_val=st.text(max_size=50),
)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_tool_wrapper_rejects_unexpected_parameters(
    bad_key: str, bad_val: str
) -> None:
    """Property test verifying strict parameter validation rejects unknown kwargs.

    Args:
        bad_key: Generated unexpected parameter name.
        bad_val: Generated parameter value.

    Notes/Architectural Intent:
        Guarantees that extraneous arguments trigger ToolValidationError to prevent
        accidental parameter pollution or injection.
    """
    container = Container()
    registry = McpServerRegistry()
    wrapper = registry._create_cqrs_tool_wrapper(
        target_cls=GeneratedCommand,
        kind="command",
        container=container,
        read_only_tool=False,
        server_read_only=False,
    )

    kwargs = {"name": "valid_user", bad_key: bad_val}
    with pytest.raises(ToolValidationError) as exc_info:
        await wrapper(**kwargs)

    err_msg = str(exc_info.value)
    assert bad_key in err_msg


@given(
    name=st.text(min_size=1, max_size=20),
)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_tool_wrapper_enforces_read_only_mode(name: str) -> None:
    """Property test verifying read-only enforcement prevents mutating commands.

    Args:
        name: Generated user string.

    Notes/Architectural Intent:
        Asserts that when server_read_only=True, mutating tools strictly raise
        ToolUnauthorizedError regardless of the input data.
    """
    container = Container()
    registry = McpServerRegistry()
    wrapper = registry._create_cqrs_tool_wrapper(
        target_cls=GeneratedCommand,
        kind="command",
        container=container,
        read_only_tool=False,
        server_read_only=True,
    )

    with pytest.raises(ToolUnauthorizedError) as exc_info:
        await wrapper(name=name)

    err_msg = str(exc_info.value)
    assert "read-only mode" in err_msg


@given(
    username=st.text(min_size=2, max_size=20),
    score=st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=30)
@pytest.mark.asyncio
async def test_tool_wrapper_handles_internal_execution_errors(
    username: str, score: int
) -> None:
    """Property test verifying unhandled bus exceptions are wrapped in ToolExecutionError.

    Args:
        username: Generated username.
        score: Generated score.

    Notes/Architectural Intent:
        Asserts that internal service crashes do not leak raw stack traces or secrets,
        wrapping errors into standardized ToolExecutionError.
    """
    container = Container()
    bus = ErrorCommandBus()
    container.add_instance(bus, declared_class=CommandBusPort)

    registry = McpServerRegistry()
    wrapper = registry._create_cqrs_tool_wrapper(
        target_cls=GeneratedPydanticCommand,
        kind="command",
        container=container,
        read_only_tool=False,
        server_read_only=False,
    )

    with pytest.raises(ToolExecutionError) as exc_info:
        await wrapper(username=username, score=score)

    err_msg = str(exc_info.value)
    assert "Internal error executing MCP tool" in err_msg
