"""Domain layer template renderers."""

from __future__ import annotations


def render_domain_init() -> str:
    return '''"""Pure domain models, CQRS messages, and business logic."""
from .commands import CreateItemCommand, ItemCreatedResponse
from .models import Item

__all__ = ["CreateItemCommand", "Item", "ItemCreatedResponse"]
'''


def render_domain_models() -> str:
    return '''"""Domain entities and value objects."""

from dataclasses import dataclass, field
import uuid


@dataclass
class Item:
    """Domain entity representing a managed item."""

    title: str
    description: str = ''
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    completed: bool = False
'''


def render_domain_commands() -> str:
    return '''"""CQRS command and query contracts."""

from hexastack_core.domain import Command
from pydantic import BaseModel


class CreateItemCommand(Command):
    """Command to create a new domain item."""

    title: str
    description: str = ''


class ItemCreatedResponse(BaseModel):
    """Result returned after item creation."""

    id: str
    title: str
'''
