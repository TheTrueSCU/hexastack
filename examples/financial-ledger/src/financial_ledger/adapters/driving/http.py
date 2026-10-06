"""FastAPI HTTP driving adapters exposing CQRS commands and queries."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from hexastack_core.utils.context import UserContext, set_user_context
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_fastapi.adapters.dependencies import get_pipeline
from hexastack_fastapi.adapters.routing import CqrsRouter

from financial_ledger.domain.commands import (
    CreateAccountCommand,
    CreateAccountResponse,
    FreezeAccountCommand,
    FreezeAccountResponse,
    GetAccountBalanceQuery,
    GetAccountBalanceResponse,
    ListLedgerEntriesQuery,
    ListLedgerEntriesResponse,
    RecordTransactionCommand,
    RecordTransactionResponse,
    TransferMoneyCommand,
    TransferMoneyResponse,
)
from financial_ledger.domain.exceptions import (
    AccountAlreadyExistsError,
    AccountFrozenError,
    AccountNotFoundError,
    ConcurrencyConflictError,
    InsufficientFundsError,
    InvalidAmountError,
    UnbalancedTransactionError,
)

__all__ = [
    "get_user_context",
    "router",
]

router = CqrsRouter(tags=["ledger"])


def get_user_context(
    authorization: Annotated[str | None, Header()] = None,
    x_tenant_id: Annotated[str | None, Header()] = None,
) -> UserContext:
    """Extract authenticated caller identity and tenant context."""
    tenant_id = x_tenant_id or "default"
    user_id = "system"
    roles = ["user"]
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if ":" in token:
            role, user_id = token.split(":", 1)
            roles = [role]
        else:
            user_id = token
    ctx = UserContext(user_id=user_id, roles=roles, tenant_id=tenant_id)
    set_user_context(ctx)
    return ctx


@router.post("/accounts", status_code=201, summary="Create a new Ledger Account")
def create_account(
    cmd: CreateAccountCommand,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    user: Annotated[UserContext, Depends(get_user_context)],
) -> CreateAccountResponse:
    if (not cmd.tenant_id or cmd.tenant_id == "default") and (
        user.tenant_id and user.tenant_id != "default"
    ):
        cmd = CreateAccountCommand(
            account_id=cmd.account_id,
            tenant_id=user.tenant_id,
            owner_id=cmd.owner_id or user.user_id,
            currency=cmd.currency,
            initial_balance=cmd.initial_balance,
            credit_limit=cmd.credit_limit,
        )
    try:
        return pipeline.execute(cmd)
    except AccountAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post("/accounts/freeze", summary="Freeze an active account")
def freeze_account(
    cmd: FreezeAccountCommand,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    user: Annotated[UserContext, Depends(get_user_context)],
) -> FreezeAccountResponse:
    try:
        return pipeline.execute(cmd)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/transfers", summary="Transfer money between accounts")
def transfer_money(
    cmd: TransferMoneyCommand,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    user: Annotated[UserContext, Depends(get_user_context)],
) -> TransferMoneyResponse:
    try:
        return pipeline.execute(cmd)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ConcurrencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (InsufficientFundsError, InvalidAmountError, AccountFrozenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/transactions", summary="Record double-entry transaction")
def record_transaction(
    cmd: RecordTransactionCommand,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    user: Annotated[UserContext, Depends(get_user_context)],
) -> RecordTransactionResponse:
    try:
        return pipeline.execute(cmd)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ConcurrencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (
        UnbalancedTransactionError,
        InvalidAmountError,
        AccountFrozenError,
        InsufficientFundsError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.get("/accounts/{account_id}/balance", summary="Get account balance")
def get_balance(
    account_id: str,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    user: Annotated[UserContext, Depends(get_user_context)],
) -> GetAccountBalanceResponse:
    try:
        return pipeline.execute(GetAccountBalanceQuery(account_id=account_id))
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/accounts/{account_id}/entries", summary="List account entries")
def list_entries(
    account_id: str,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
    user: Annotated[UserContext, Depends(get_user_context)],
) -> ListLedgerEntriesResponse:
    return pipeline.execute(ListLedgerEntriesQuery(account_id=account_id))
