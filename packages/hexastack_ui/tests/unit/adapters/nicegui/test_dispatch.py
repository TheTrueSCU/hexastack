"""Unit tests for NiceGUI CQRS dispatch helpers."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from hexastack_core.domain import Command, Query
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_ui.adapters.nicegui.dispatch import (
    dispatch_command,
    dispatch_query,
)


@dataclass(frozen=True)
class CreateItem(Command):
    name: str


@dataclass(frozen=True)
class GetItem(Query):
    item_id: str


@pytest.mark.anyio
async def test_dispatch_command_sync_and_async():
    """Verify dispatch_command supports sync and awaitable pipeline execution."""
    pipeline_mock = MagicMock(spec=ExecutionPipeline)
    pipeline_mock.execute = MagicMock(return_value="created-123")

    cmd = CreateItem(name="Widget")
    result = await dispatch_command(pipeline_mock, cmd)
    assert result == "created-123"

    async def async_res():
        return "async-created"

    pipeline_mock.execute = MagicMock(return_value=async_res())
    result_async = await dispatch_command(pipeline_mock, cmd)
    assert result_async == "async-created"


@pytest.mark.anyio
async def test_dispatch_query_sync_and_async():
    """Verify dispatch_query supports sync and awaitable pipeline execution."""
    pipeline_mock = MagicMock(spec=ExecutionPipeline)
    pipeline_mock.execute = MagicMock(return_value="widget-data")

    qry = GetItem(item_id="123")
    result = await dispatch_query(pipeline_mock, qry)
    assert result == "widget-data"

    async def async_res():
        return "async-query"

    pipeline_mock.execute = MagicMock(return_value=async_res())
    result_async = await dispatch_query(pipeline_mock, qry)
    assert result_async == "async-query"
