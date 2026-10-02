"""FastAPI HTTP driving adapters exposing CQRS commands and queries."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
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
    InsufficientFundsError,
    InvalidAmountError,
    UnbalancedTransactionError,
)

__all__ = [
    "router",
]

router = CqrsRouter(tags=["ledger"])


@router.post("/accounts", status_code=201, summary="Create a new Ledger Account")
def create_account(
    cmd: CreateAccountCommand,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
) -> CreateAccountResponse:
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
) -> TransferMoneyResponse:
    try:
        return pipeline.execute(cmd)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (InsufficientFundsError, InvalidAmountError, AccountFrozenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/transactions", summary="Record double-entry transaction")
def record_transaction(
    cmd: RecordTransactionCommand,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
) -> RecordTransactionResponse:
    try:
        return pipeline.execute(cmd)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
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
) -> ListLedgerEntriesResponse:
    return pipeline.execute(ListLedgerEntriesQuery(account_id=account_id))
