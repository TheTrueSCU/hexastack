"""Test suite template renderers."""

from __future__ import annotations


def render_test_conftest(package_name: str) -> str:
    return f'''"""Shared pytest fixtures."""

import pytest
from {package_name}.adapters.driven.database import InMemoryItemRepository


@pytest.fixture
def item_repo():
    return InMemoryItemRepository()
'''


def render_test_domain(package_name: str) -> str:
    return f'''"""Unit tests verifying pure domain models and handlers."""

from {package_name}.domain.commands import CreateItemCommand
from {package_name}.domain.models import Item
from {package_name}.infra.handlers import handle_create_item


def test_item_entity_creation():
    item = Item(title="Buy Milk")
    assert item.title == "Buy Milk"
    assert not item.completed
    assert item.id is not None


def test_handle_create_item(item_repo):
    cmd = CreateItemCommand(title="Ship Release", description="v1.0")
    res = handle_create_item(cmd, repo=item_repo)
    assert res.title == "Ship Release"
    saved = item_repo.get_by_id(res.id)
    assert saved is not None
    assert saved.description == "v1.0"
'''


def render_test_domain_fuzz(package_name: str) -> str:
    return f'''"""Property-based fuzzing tests for domain entities."""

from hypothesis import given, strategies as st
from {package_name}.domain.models import Item


@given(title=st.text(min_size=1), description=st.text())
def test_item_property_invariants(title: str, description: str):
    item = Item(title=title, description=description)
    assert item.title == title
    assert item.description == description
    assert len(item.id) > 0
'''
