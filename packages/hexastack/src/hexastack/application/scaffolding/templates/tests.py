"""Test suite template renderers.

Notes/Architectural Intent:
    Provides template renderers for 1:1 test directory parity, property-based fuzzing,
    and hexagonal architecture boundary compliance tests.
"""

from __future__ import annotations


def render_test_conftest(package_name: str) -> str:
    """Render root conftest.py fixtures.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Shared pytest fixtures."""

import pytest
from {package_name}.adapters.driven.database import InMemoryItemRepository


@pytest.fixture
def item_repo():
    """Provide a clean in-memory item repository fixture."""
    return InMemoryItemRepository()
'''


def render_test_architecture(package_name: str) -> str:
    """Render hexagonal architecture boundary test suite.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Hexagonal architecture boundary tests for {package_name}."""

from hexastack_core.testing import assert_clean_architecture


def test_{package_name}_clean_architecture():
    """Assert {package_name} strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("{package_name}")
'''


def render_test_domain(package_name: str) -> str:
    """Render legacy/fallback domain unit tests.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests verifying pure domain models and handlers."""

from {package_name}.domain.commands import CreateItemCommand
from {package_name}.domain.models import Item
from {package_name}.infra.handlers import handle_create_item


def test_item_entity_creation():
    """Verify Item entity creation with default values."""
    item = Item(title="Buy Milk")
    res_title = item.title
    res_completed = item.completed
    assert res_title == "Buy Milk"
    assert not res_completed
    assert item.id is not None


def test_handle_create_item(item_repo):
    """Verify item creation handler persists to repository."""
    cmd = CreateItemCommand(title="Ship Release", description="v1.0")
    res = handle_create_item(cmd, repo=item_repo)
    res_title = res.title
    assert res_title == "Ship Release"
    saved = item_repo.get_by_id(res.id)
    assert saved is not None
    assert saved.description == "v1.0"
'''


def render_test_domain_models(package_name: str) -> str:
    """Render unit tests for domain models.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests verifying Item domain model."""

from {package_name}.domain.models import Item


def test_item_creation():
    """Verify Item entity creation with default and custom values."""
    item = Item(title="Test Item", description="Test Description")
    res_title = item.title
    res_completed = item.completed
    assert res_title == "Test Item"
    assert res_completed is False
    assert item.id is not None
'''


def render_test_domain_commands(package_name: str) -> str:
    """Render unit tests for domain commands.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests verifying domain CQRS commands."""

from {package_name}.domain.commands import CreateItemCommand, ItemCreatedResponse


def test_create_item_command():
    """Verify CreateItemCommand instantiation and field values."""
    cmd = CreateItemCommand(title="New Task", description="Details")
    res_title = cmd.title
    assert res_title == "New Task"


def test_item_created_response():
    """Verify ItemCreatedResponse model."""
    resp = ItemCreatedResponse(id="item-123", title="New Task")
    res_id = resp.id
    assert res_id == "item-123"
'''


def render_test_ports_repositories(package_name: str) -> str:
    """Render unit tests for repository ports.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests verifying ItemRepositoryPort interface."""

from {package_name}.ports.repositories import ItemRepositoryPort


def test_item_repository_port_abstract():
    """Verify ItemRepositoryPort declares abstract methods."""
    abstract_methods = ItemRepositoryPort.__abstractmethods__
    assert abstract_methods == frozenset({{"get_by_id", "save"}})
'''


def render_test_adapters_database(package_name: str) -> str:
    """Render unit tests for database adapters.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests for InMemoryItemRepository adapter."""

from {package_name}.adapters.driven.database import InMemoryItemRepository
from {package_name}.domain.models import Item


def test_in_memory_repository_save_and_get():
    """Verify saving and retrieving items in memory."""
    repo = InMemoryItemRepository()
    item = Item(title="Persisted Item")
    repo.save(item)
    saved = repo.get_by_id(item.id)
    assert saved is not None
    assert saved.title == "Persisted Item"


def test_in_memory_repository_get_nonexistent():
    """Verify get_by_id returns None for nonexistent item."""
    repo = InMemoryItemRepository()
    res = repo.get_by_id("non-existent")
    assert res is None
'''


def render_test_adapters_cli(package_name: str) -> str:
    """Render unit tests for CLI driving adapter.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests for CLI driving adapter."""

from unittest.mock import MagicMock, patch
import pytest
from {package_name}.adapters.driving.cli import main


def test_cli_module_loaded():
    """Verify CLI main entrypoint is callable."""
    is_callable = callable(main)
    assert is_callable is True


def test_cli_main_success():
    """Verify CLI main invokes cli_app when available."""
    mock_cli = MagicMock()
    with patch(
        "{package_name}.infra.bootstrap.create_app",
        return_value={{"cli_app": mock_cli}},
    ):
        main()
        called = mock_cli.called
        assert called is True


def test_cli_main_failure():
    """Verify CLI main exits when cli_app is missing."""
    with patch("{package_name}.infra.bootstrap.create_app", return_value={{}}):
        with pytest.raises(SystemExit) as exc_info:
            main()
        code = exc_info.value.code
        assert code == 1
'''


def render_test_adapters_http(package_name: str) -> str:
    """Render unit tests for HTTP driving adapter.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests for HTTP driving adapter."""

import {package_name}.adapters.driving.http as http_adapter


def test_http_adapter_loaded():
    """Verify HTTP driving adapter loads cleanly."""
    assert http_adapter is not None
'''


def render_test_adapters_grpc(package_name: str) -> str:
    """Render unit tests for gRPC driving adapter.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests for gRPC driving adapter."""

import {package_name}.adapters.driving.grpc as grpc_adapter


def test_grpc_adapter_loaded():
    """Verify gRPC driving adapter loads cleanly."""
    assert grpc_adapter is not None
'''


def render_test_adapters_graphql(package_name: str) -> str:
    """Render unit tests for GraphQL driving adapter.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests for GraphQL driving adapter."""

import {package_name}.adapters.driving.graphql as graphql_adapter


def test_graphql_adapter_loaded():
    """Verify GraphQL driving adapter loads cleanly."""
    assert graphql_adapter is not None
'''


def render_test_adapters_mcp(package_name: str) -> str:
    """Render unit tests for MCP driving adapter.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests for MCP driving adapter."""

import {package_name}.adapters.driving.mcp as mcp_adapter


def test_mcp_adapter_loaded():
    """Verify MCP driving adapter loads cleanly."""
    assert mcp_adapter is not None
'''


def render_test_infra_config(package_name: str) -> str:
    """Render unit tests for service config.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests for service configuration."""

from {package_name}.infra.config import AppConfig


def test_app_config_defaults():
    """Verify default AppConfig settings."""
    cfg = AppConfig()
    res_env = cfg.environment
    assert res_env == "development"
'''


def render_test_infra_handlers(package_name: str) -> str:
    """Render unit tests for CQRS handlers.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests for CQRS handlers."""

from {package_name}.adapters.driven.database import InMemoryItemRepository
from {package_name}.domain.commands import CreateItemCommand
from {package_name}.infra.handlers import handle_create_item


def test_handle_create_item():
    """Verify handle_create_item persists and returns created response."""
    repo = InMemoryItemRepository()
    cmd = CreateItemCommand(title="Handled Item", description="From test")
    resp = handle_create_item(cmd, repo=repo)
    res_title = resp.title
    assert res_title == "Handled Item"
    saved = repo.get_by_id(resp.id)
    assert saved is not None
'''


def render_test_infra_bootstrap(package_name: str) -> str:
    """Render unit tests for application bootstrap.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests for application bootstrap."""

from {package_name}.infra.bootstrap import create_app


def test_create_app_bootstraps_successfully():
    """Verify create_app constructs container without error."""
    app = create_app()
    assert app is not None
'''


def render_test_root_init(package_name: str) -> str:
    """Render unit tests for root package __init__.py.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Unit tests for root package initialization."""

import {package_name}


def test_package_has_docstring():
    """Verify root package contains module docstring."""
    doc = {package_name}.__doc__
    assert doc is not None
'''


def render_test_subpackage_init(package_name: str, subpath: str) -> str:
    """Render unit tests for subpackage __init__.py.

    Args:
        package_name: Name of the scaffolded package.
        subpath: Subpackage dot-separated path (e.g. 'domain', 'ports').

    Returns:
        Rendered python source content.
    """
    fn_name = subpath.replace(".", "_")
    return f'''"""Unit tests for {subpath} package initialization."""

import {package_name}.{subpath}


def test_{fn_name}_package_loaded():
    """Verify subpackage imports cleanly."""
    doc = {package_name}.{subpath}.__doc__
    assert doc is not None
'''


def render_test_domain_fuzz(package_name: str) -> str:
    """Render property-based fuzzing tests for domain entities.

    Args:
        package_name: Name of the scaffolded package.

    Returns:
        Rendered python source content.
    """
    return f'''"""Property-based fuzzing tests for domain entities."""

from hypothesis import given, strategies as st
from {package_name}.domain.models import Item


@given(title=st.text(min_size=1), description=st.text())
def test_item_property_invariants(title: str, description: str):
    """Verify invariants hold across randomized item inputs."""
    item = Item(title=title, description=description)
    res_title = item.title
    res_desc = item.description
    assert res_title == title
    assert res_desc == description
    assert len(item.id) > 0
'''


__all__ = [
    "render_test_adapters_cli",
    "render_test_adapters_database",
    "render_test_adapters_graphql",
    "render_test_adapters_grpc",
    "render_test_adapters_http",
    "render_test_adapters_mcp",
    "render_test_architecture",
    "render_test_conftest",
    "render_test_domain",
    "render_test_domain_commands",
    "render_test_domain_fuzz",
    "render_test_domain_models",
    "render_test_infra_bootstrap",
    "render_test_infra_config",
    "render_test_infra_handlers",
    "render_test_ports_repositories",
    "render_test_root_init",
    "render_test_subpackage_init",
]
