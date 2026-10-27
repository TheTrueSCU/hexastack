"""Unit and dual-oracle verification tests for RFC 6901 JSON pointer utilities.

Notes/Architectural Intent:
    Verifies that resolve_pointer, set_pointer, and escaping routines strictly
    adhere to the RFC 6901 specification and maintain equivalence against
    the reference jsonpointer package.
"""

from typing import Any, cast

import pytest
from hypothesis import given
from hypothesis import strategies as st

from hexastack_core.domain.exceptions import PointerResolutionError
from hexastack_core.domain.pointers import (
    escape_pointer,
    extract_pointers,
    resolve_pointer,
    set_pointer,
    unescape_pointer,
)
from hexastack_core.testing import require_extra
from hexastack_core.utils.imports import optional_dependency

jsonpointer = optional_dependency("jsonpointer")


def test_escape_and_unescape_pointer() -> None:
    """Test RFC 6901 escaping rules (~ -> ~0, / -> ~1)."""
    raw = "user/name~profile"
    escaped = escape_pointer(raw)
    assert escaped == "user~1name~0profile"

    unescaped = unescape_pointer(escaped)
    assert unescaped == raw


def test_resolve_pointer_root() -> None:
    """Test resolving empty root pointer."""
    doc = {"hello": "world"}
    resolved = resolve_pointer(doc, "")
    assert resolved == doc


def test_resolve_pointer_nested_dict_and_list() -> None:
    """Test standard dictionary and list traversal."""
    doc = {
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ],
        "settings": {
            "theme": "dark",
            "active": True,
        },
    }

    user_name = resolve_pointer(doc, "/users/1/name")
    assert user_name == "Bob"

    theme = resolve_pointer(doc, "/settings/theme")
    assert theme == "dark"

    active = resolve_pointer(doc, "/settings/active")
    assert active is True


def test_resolve_pointer_escaped_characters() -> None:
    """Test resolving keys containing slashes and tildes."""
    doc = {
        "a/b": {"c~d": "target"},
    }

    resolved = resolve_pointer(doc, "/a~1b/c~0d")
    assert resolved == "target"


def test_resolve_pointer_default_fallback() -> None:
    """Test that missing keys return default when provided."""
    doc = {"a": 1}

    fallback = resolve_pointer(doc, "/b/c", default="fallback")
    assert fallback == "fallback"

    fallback_idx = resolve_pointer([1, 2], "/10", default="out_of_bounds")
    assert fallback_idx == "out_of_bounds"


def test_resolve_pointer_errors() -> None:
    """Test resolution failures and error formatting."""
    doc = {"users": [{"name": "test"}]}

    with pytest.raises(PointerResolutionError, match="must start with '/'"):
        resolve_pointer(doc, "users/0/name")

    with pytest.raises(PointerResolutionError, match="must be a string"):
        resolve_pointer(doc, cast("str", 123))

    with pytest.raises(PointerResolutionError, match="not found"):
        resolve_pointer(doc, "/users/0/age")

    with pytest.raises(PointerResolutionError, match="Negative list index"):
        resolve_pointer(doc, "/users/-1")

    with pytest.raises(
        PointerResolutionError, match="Cannot traverse into non-container"
    ):
        resolve_pointer(doc, "/users/0/name/extra")


def test_set_pointer_existing_and_new_keys() -> None:
    """Test mutating existing documents with set_pointer."""
    doc: dict[str, Any] = {"config": {"retries": 3}}

    set_pointer(doc, "/config/retries", 5)
    retries = doc["config"]["retries"]
    assert retries == 5

    set_pointer(doc, "/config/timeout", 30)
    timeout = doc["config"]["timeout"]
    assert timeout == 30


def test_set_pointer_intermediate_creation() -> None:
    """Test auto-creating intermediate nested structures."""
    doc: dict[str, Any] = {}

    set_pointer(doc, "/a/b/c", "deep")
    deep_val = doc["a"]["b"]["c"]
    assert deep_val == "deep"


def test_set_pointer_list_append_hyphen() -> None:
    """Test appending to list with RFC 6901 '-' token."""
    doc: dict[str, Any] = {"items": [1, 2]}

    set_pointer(doc, "/items/-", 3)
    items = doc["items"]
    assert items == [1, 2, 3]


def test_set_pointer_not_inplace() -> None:
    """Test setting pointer with inplace=False."""
    doc = {"a": 1}
    updated = set_pointer(doc, "/b", 2, inplace=False)

    assert doc == {"a": 1}
    assert updated == {"a": 1, "b": 2}


def test_set_pointer_invalid_pointer_raises() -> None:
    """Test that invalid pointers raise PointerResolutionError."""
    with pytest.raises(PointerResolutionError, match="non-empty string"):
        set_pointer({}, "", 1)


def test_set_pointer_list_and_container_branches() -> None:
    """Test setting values in nested lists and handling container errors."""
    # 1. Setting index in existing list
    doc_list: list[Any] = [1, 2]
    set_pointer(doc_list, "/1", 99)
    assert doc_list[1] == 99

    # 2. Setting index beyond current length (auto-padding with None)
    set_pointer(doc_list, "/4", "tail")
    assert len(doc_list) == 5
    assert doc_list[4] == "tail"
    assert doc_list[2] is None

    # 3. Navigating through list intermediate
    nested_list: list[Any] = []
    set_pointer(nested_list, "/0/key", "val")
    assert nested_list[0]["key"] == "val"

    # 4. Invalid list indices
    with pytest.raises(PointerResolutionError, match="Invalid list index"):
        set_pointer([], "/not_a_number", "x")

    with pytest.raises(PointerResolutionError, match="Invalid list index"):
        set_pointer([[]], "/not_a_number/key", "x")

    # 5. Setting on non-container
    with pytest.raises(
        PointerResolutionError, match="Cannot set value on non-container"
    ):
        set_pointer(42, "/sub", "fail")

    with pytest.raises(
        PointerResolutionError, match="Cannot traverse into non-container"
    ):
        set_pointer(42, "/a/b", "fail")


def test_extract_pointers() -> None:
    """Test extracting all pointers from a document."""
    doc = {
        "user": {"name": "Alice"},
        "tags": ["python", "hexagonal"],
    }

    ptrs = extract_pointers(doc)
    assert "/user" in ptrs
    assert "/user/name" in ptrs
    assert "/tags" in ptrs
    assert "/tags/0" in ptrs
    assert "/tags/1" in ptrs

    # Verify every extracted pointer resolves back without error
    for p in ptrs:
        val = resolve_pointer(doc, p)
        assert val is not None


@require_extra("jsonpointer")
@given(
    st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
        values=st.one_of(
            st.integers(min_value=0, max_value=100),
            st.text(min_size=0, max_size=10),
            st.lists(st.integers(min_value=0, max_value=50), max_size=5),
        ),
        max_size=5,
    )
)
def test_dual_oracle_jsonpointer_equivalence(doc: dict[str, Any]) -> None:
    """Dual-oracle testing: verify parity between built-in resolver and external jsonpointer."""
    assert jsonpointer is not None
    pointers = extract_pointers(doc)

    for ptr in pointers:
        res_builtin = resolve_pointer(doc, ptr)
        res_oracle = jsonpointer.resolve_pointer(doc, ptr)
        assert res_builtin == res_oracle
