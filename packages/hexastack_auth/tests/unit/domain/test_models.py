from hexastack_auth.domain.models import AnonymousIdentity, Identity, TokenPayload


def test_identity_methods():
    identity = Identity(
        user_id="usr_test",
        roles=frozenset(["admin", "manager"]),
        permissions=frozenset(["read", "write", "delete"]),
        tenant_id="tenant_1",
    )

    assert identity.is_authenticated is True
    assert identity.has_role("admin") is True
    assert identity.has_role("guest") is False

    assert identity.has_permission("write") is True
    assert identity.has_permission("execute") is False

    assert identity.has_all_roles(["admin", "manager"]) is True
    assert identity.has_all_roles(["admin", "superadmin"]) is False

    assert identity.has_any_role(["superadmin", "manager"]) is True
    assert identity.has_any_role(["superadmin", "guest"]) is False

    assert identity.has_all_permissions(["read", "write"]) is True
    assert identity.has_all_permissions(["read", "execute"]) is False

    assert identity.has_any_permission(["execute", "delete"]) is True
    assert identity.has_any_permission(["execute", "audit"]) is False


def test_anonymous_identity():
    anon = AnonymousIdentity()
    assert anon.user_id == "anonymous"
    assert anon.is_authenticated is False
    assert len(anon.roles) == 0
    assert len(anon.permissions) == 0
    assert anon.has_role("admin") is False
    assert anon.has_permission("read") is False


def test_token_payload():
    payload = TokenPayload(
        subject="usr_123",
        roles=["admin"],
        permissions=["read"],
        tenant_id="tenant_42",
        custom_claims={"email": "test@example.com"},
    )
    assert payload.subject == "usr_123"
    assert payload.roles == ["admin"]
    assert payload.custom_claims["email"] == "test@example.com"
