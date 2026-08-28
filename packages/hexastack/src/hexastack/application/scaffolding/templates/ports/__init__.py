"""Ports layer template renderers."""

from __future__ import annotations


def render_ports_init() -> str:
    return '''"""Secondary abstract port interfaces."""
from .repositories import ItemRepositoryPort

__all__ = ["ItemRepositoryPort"]
'''


def render_ports_repositories(package_name: str) -> str:
    return f'''"""Abstract storage repository ports."""

from abc import ABC, abstractmethod
from typing import Optional
from {package_name}.domain.models import Item


class ItemRepositoryPort(ABC):
    """Abstract repository port for persisting Item entities."""

    @abstractmethod
    def save(self, item: Item) -> None:
        """Persist an item."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, item_id: str) -> Optional[Item]:
        """Retrieve an item by identifier."""
        raise NotImplementedError
'''
