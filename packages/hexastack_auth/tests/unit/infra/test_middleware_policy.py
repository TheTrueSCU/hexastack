from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from hexastack_auth.domain.exceptions import InsufficientPermissionsError
from hexastack_auth.infra.decorators import authorize
from hexastack_auth.infra.middleware import AuthorizationMiddleware
from hexastack_core.domain import Command
from hexastack_core.utils.context import (
    UserContext,
    correlation_scope,
    set_user_context,
)


@authorize(policy="policies.finance.approve")
@dataclass(frozen=True)
class ApproveInvoice(Command):
    invoice_id: str


@authorize(relation="editor", object_type="doc", object_id_field="doc_id")
@dataclass(frozen=True)
class EditDoc(Command):
    doc_id: str


@authorize(spiffe_ids=["spiffe://example.org/billing"])
@dataclass(frozen=True)
class SyncBilling(Command):
    tx_id: str


def test_opa_policy_middleware_allowed():
    policy_mock = MagicMock()
    policy_mock.is_authorized.return_value = True

    mw = AuthorizationMiddleware(enabled=True, policy_adapter=policy_mock)
    cmd = ApproveInvoice(invoice_id="inv-1")

    with correlation_scope("test-corr"):
        set_user_context(UserContext(user_id="alice", roles=["finance"]))
        res = mw(cmd, lambda c: "ok")
        assert res == "ok"
        policy_mock.is_authorized.assert_called_once()


def test_opa_policy_middleware_denied():
    policy_mock = MagicMock()
    policy_mock.is_authorized.return_value = False

    mw = AuthorizationMiddleware(enabled=True, policy_adapter=policy_mock)
    cmd = ApproveInvoice(invoice_id="inv-1")

    with correlation_scope("test-corr"):
        set_user_context(UserContext(user_id="alice", roles=["finance"]))
        with pytest.raises(InsufficientPermissionsError) as exc:
            mw(cmd, lambda c: "ok")
        assert "denied by policy" in str(exc.value)


def test_spiffe_workload_middleware_denied():
    mw = AuthorizationMiddleware(enabled=True)
    cmd = SyncBilling(tx_id="tx-1")

    with correlation_scope("test-corr"):
        # Caller does not have spiffe_id in claims
        set_user_context(UserContext(user_id="billing-service", roles=[]))
        with pytest.raises(InsufficientPermissionsError) as exc:
            mw(cmd, lambda c: "ok")
        assert "Caller SPIFFE identity" in str(exc.value)
