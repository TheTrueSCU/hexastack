from hexastack_auth.infra.decorators import (
    AuthMetadata,
    authenticated,
    authorize,
    get_auth_metadata,
    requires_permission,
    requires_role,
)
from hexastack_core.domain import Command


def test_auth_metadata_defaults():
    meta = AuthMetadata()
    assert meta.roles == ()
    assert meta.permissions == ()
    assert meta.require_authenticated is True
    assert meta.match_all_roles is True
    assert meta.match_all_permissions is True


def test_authorize_decorator():
    @authorize(
        roles=["admin", "superadmin"],
        permissions=["users:ban", "users:delete"],
        require_authenticated=True,
        match_all_roles=False,
        match_all_permissions=False,
    )
    class BanUserCommand(Command):
        user_id: str

    meta = get_auth_metadata(BanUserCommand)
    assert meta is not None
    assert meta.roles == ("admin", "superadmin")
    assert meta.permissions == ("users:ban", "users:delete")
    assert meta.require_authenticated is True
    assert meta.match_all_roles is False
    assert meta.match_all_permissions is False


def test_convenience_decorators():
    @authenticated()
    class ViewProfileQuery:
        pass

    meta_auth = get_auth_metadata(ViewProfileQuery)
    assert meta_auth is not None
    assert meta_auth.require_authenticated is True
    assert meta_auth.roles == ()
    assert meta_auth.permissions == ()
    assert meta_auth.match_all_roles is True
    assert meta_auth.match_all_permissions is True

    @requires_role("manager", "director")
    class ApproveExpenseCommand:
        pass

    meta_role = get_auth_metadata(ApproveExpenseCommand)
    assert meta_role is not None
    assert meta_role.roles == ("manager", "director")
    assert meta_role.permissions == ()
    assert meta_role.require_authenticated is True

    @requires_permission("invoices:pay", "invoices:approve")
    class PayInvoiceCommand:
        pass

    meta_perm = get_auth_metadata(PayInvoiceCommand)
    assert meta_perm is not None
    assert meta_perm.permissions == ("invoices:pay", "invoices:approve")
    assert meta_perm.roles == ()
    assert meta_perm.require_authenticated is True


def test_get_auth_metadata_on_instances_and_none():
    assert get_auth_metadata(None) is None
    assert get_auth_metadata(object()) is None

    @requires_role("admin")
    class SampleCommand(Command):
        pass

    cmd_instance = SampleCommand()
    meta = get_auth_metadata(cmd_instance)
    assert meta is not None
    assert meta.roles == ("admin",)
    assert meta.permissions == ()
