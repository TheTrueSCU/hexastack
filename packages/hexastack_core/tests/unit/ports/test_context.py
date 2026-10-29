from __future__ import annotations

from hexastack_core.ports.context import ContextVarPort, TokenPort
from hexastack_core.utils.context import (
    ContextVar,
    Token,
    create_context_var,
)


def test_token_satisfies_token_port():
    token = Token(old_value="initial")
    is_proto = isinstance(token, TokenPort)
    assert is_proto is True
    assert token.old_value == "initial"


def test_context_var_satisfies_context_var_port():
    var: ContextVarPort[str] = ContextVar("test_var", default="default_val")
    is_proto = isinstance(var, ContextVarPort)
    assert is_proto is True
    assert var.name == "test_var"

    initial_val = var.get()
    assert initial_val == "default_val"

    tok = var.set("updated_val")
    is_tok_proto = isinstance(tok, TokenPort)
    assert is_tok_proto is True

    curr_val = var.get()
    assert curr_val == "updated_val"

    var.reset(tok)
    reset_val = var.get()
    assert reset_val == "default_val"


def test_create_context_var_factory():
    var = create_context_var("tenant_id", default="t-001")
    is_proto = isinstance(var, ContextVarPort)
    assert is_proto is True

    val = var.get()
    assert val == "t-001"
