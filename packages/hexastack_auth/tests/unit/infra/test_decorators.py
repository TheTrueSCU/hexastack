from hexastack_auth.infra.decorators import (
    authenticated,
    authorize,
    get_auth_metadata,
    requires_permission,
    requires_role,
)
from hexastack_core.domain import Command


def test_authorize_decorator():
    @authorize(roles=["admin"], permissions=["users:ban"])
    class BanUserCommand(Command):
        user_id: str

    meta = get_auth_metadata(BanUserCommand)
    assert meta is not None
    assert meta.roles == ("admin",)
    assert meta.permissions == ("users:ban",)
    assert meta.require_authenticated is True


def test_convenience_decorators():
    @authenticated()
    class ViewProfileQuery:
        pass

    meta_auth = get_auth_metadata(ViewProfileQuery)
    assert meta_auth is not None
    assert meta_auth.require_authenticated is True
    assert meta_auth.roles == ()

    @requires_role("manager", "director")
    class ApproveExpenseCommand:
        pass

    meta_role = get_auth_metadata(ApproveExpenseCommand)
    assert meta_role is not None
    assert meta_role.roles == ("manager", "director")

    @requires_permission("invoices:pay")
    class PayInvoiceCommand:
        pass

    meta_perm = get_auth_metadata(PayInvoiceCommand)
    assert meta_perm is not None
    assert meta_perm.permissions == ("invoices:pay",)


def test_get_auth_metadata_on_instances_and_none():
    assert get_auth_metadata(None) is None

    @requires_role("admin")
    class SampleCommand(Command):
        pass

    cmd_instance = SampleCommand()
    meta = get_auth_metadata(cmd_instance)
    assert meta is not None
    assert meta.roles == ("admin",)
