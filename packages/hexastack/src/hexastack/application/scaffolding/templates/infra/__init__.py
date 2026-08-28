"""Infrastructure layer template renderers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack.application.scaffolding.generator import ScaffoldConfig


def render_infra_config(config: ScaffoldConfig) -> str:
    return f'''"""Application settings and environment configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Service environment settings."""

    model_config = SettingsConfigDict(env_prefix='APP_', extra='ignore')

    service_name: str = '{config.name}'
    environment: str = 'development'
'''


def render_infra_handlers(package_name: str) -> str:
    return f'''"""Application CQRS command and query handlers."""

from {package_name}.domain.commands import CreateItemCommand, ItemCreatedResponse
from {package_name}.domain.models import Item
from {package_name}.ports.repositories import ItemRepositoryPort


def handle_create_item(cmd: CreateItemCommand, repo: ItemRepositoryPort) -> ItemCreatedResponse:
    """Handler processing CreateItemCommand."""
    item = Item(title=cmd.title, description=cmd.description)
    repo.save(item)
    return ItemCreatedResponse(id=item.id, title=item.title)
'''


def render_infra_bootstrap(config: ScaffoldConfig, package_name: str) -> str:
    scan_packages = [f"{package_name}.adapters.driving.cli"]
    extra_imports = []

    if (
        config.template in ("web-api", "enterprise", "graphql-service")
        or config.include_graphql
    ):
        scan_packages.append(f"{package_name}.adapters.driving.http")
        extra_imports.append(f"import {package_name}.adapters.driving.http")
    if config.template in ("grpc-service", "enterprise") or config.include_grpc:
        scan_packages.append(f"{package_name}.adapters.driving.grpc")
        extra_imports.append(f"import {package_name}.adapters.driving.grpc")
    if config.template in ("graphql-service", "enterprise") or config.include_graphql:
        scan_packages.append(f"{package_name}.adapters.driving.graphql")
        extra_imports.append(f"import {package_name}.adapters.driving.graphql")
    if config.template in ("mcp-agent", "enterprise") or config.include_mcp:
        scan_packages.append(f"{package_name}.adapters.driving.mcp")
        extra_imports.append(f"import {package_name}.adapters.driving.mcp")

    packages_list_str = ",\n            ".join(scan_packages)
    extra_imports_str = "\n".join(extra_imports)

    return f'''"""Hexastack bootstrapper and application assembly."""

from typing import Any
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_cqrs.infra.decorators import command_handler
import {package_name}.adapters.driving.cli
{extra_imports_str}
from {package_name}.adapters.driven.database import InMemoryItemRepository
from {package_name}.domain.commands import CreateItemCommand
from {package_name}.infra.handlers import handle_create_item
from {package_name}.ports.repositories import ItemRepositoryPort

# Bind command handler
command_handler(CreateItemCommand)(handle_create_item)


def create_app() -> Any:
    """Bootstrap full Hexastack microservice kernel."""
    result = bootstrap(
        packages_to_scan=[
            {packages_list_str},
        ],
    )
    repo = InMemoryItemRepository()
    result.container.add_instance(repo, declared_class=ItemRepositoryPort)
    return result
'''
