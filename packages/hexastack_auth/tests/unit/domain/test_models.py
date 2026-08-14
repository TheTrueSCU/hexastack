from hexastack_auth.domain.models import AnonymousIdentity, Identity, TokenPayload


def test_identity_default_construction():
    ident = Identity(user_id="usr_default")
    assert ident.user_id == "usr_default"
    assert ident.roles == frozenset()
    assert ident.permissions == frozenset()
    assert ident.tenant_id is None
    assert ident.claims == {}
    assert ident.is_authenticated is True

    # Empty collection checks
    assert ident.has_all_roles([]) is True
    assert ident.has_any_role([]) is False
    assert ident.has_all_permissions([]) is True
    assert ident.has_any_permission([]) is False


def test_identity_methods():
    identity = Identity(
        user_id="usr_test",
        roles=frozenset(["admin", "manager"]),
        permissions=frozenset(["read", "write", "delete"]),
        tenant_id="tenant_1",
        claims={"org": "engineering"},
        is_authenticated=True,
    )

    assert identity.is_authenticated is True
    assert identity.tenant_id == "tenant_1"
    assert identity.claims["org"] == "engineering"

    # Single role checks
    assert identity.has_role("admin") is True
    assert identity.has_role("manager") is True
    assert identity.has_role("guest") is False
    assert identity.has_role("") is False

    # Single permission checks
    assert identity.has_permission("write") is True
    assert identity.has_permission("read") is True
    assert identity.has_permission("delete") is True
    assert identity.has_permission("execute") is False
    assert identity.has_permission("") is False

    # Multiple role checks
    assert identity.has_all_roles(["admin", "manager"]) is True
    assert identity.has_all_roles(["admin"]) is True
    assert identity.has_all_roles(["admin", "superadmin"]) is False
    assert identity.has_all_roles(["guest"]) is False

    assert identity.has_any_role(["superadmin", "manager"]) is True
    assert identity.has_any_role(["admin"]) is True
    assert identity.has_any_role(["superadmin", "guest"]) is False

    # Multiple permission checks
    assert identity.has_all_permissions(["read", "write"]) is True
    assert identity.has_all_permissions(["read", "write", "delete"]) is True
    assert identity.has_all_permissions(["read", "execute"]) is False

    assert identity.has_any_permission(["execute", "delete"]) is True
    assert identity.has_any_permission(["read"]) is True
    assert identity.has_any_permission(["execute", "audit"]) is False


def test_anonymous_identity():
    anon = AnonymousIdentity()
    assert anon.user_id == "anonymous"
    assert anon.is_authenticated is False
    assert anon.tenant_id is None
    assert anon.claims == {}
    assert len(anon.roles) == 0
    assert len(anon.permissions) == 0
    assert anon.has_role("admin") is False
    assert anon.has_permission("read") is False
    assert anon.has_any_role(["admin", "guest"]) is False
    assert anon.has_all_roles(["admin"]) is False
    assert anon.has_any_permission(["read"]) is False
    assert anon.has_all_permissions(["read"]) is False


def test_token_payload():
    payload_def = TokenPayload(subject="usr_plain")
    assert payload_def.subject == "usr_plain"
    assert payload_def.roles == []
    assert payload_def.permissions == []
    assert payload_def.tenant_id is None
    assert payload_def.custom_claims == {}
    assert payload_def.expires_at is None
    assert payload_def.issued_at is None

    payload = TokenPayload(
        subject="usr_123",
        roles=["admin"],
        permissions=["read"],
        tenant_id="tenant_42",
        custom_claims={"email": "test@example.com"},
        expires_at=1700000000,
        issued_at=1699996400,
    )
    assert payload.subject == "usr_123"
    assert payload.roles == ["admin"]
    assert payload.permissions == ["read"]
    assert payload.tenant_id == "tenant_42"
    assert payload.custom_claims["email"] == "test@example.com"
    assert payload.expires_at == 1700000000
    assert payload.issued_at == 1699996400
