"""Shared pytest fixtures for Financial Ledger test suite."""

from __future__ import annotations

import pytest

from financial_ledger.adapters.driven.database import (
    InMemoryAccountRepository,
    InMemoryLedgerRepository,
)


@pytest.fixture
def account_repo() -> InMemoryAccountRepository:
    """Provide isolated in-memory account repository."""
    return InMemoryAccountRepository()


@pytest.fixture
def ledger_repo() -> InMemoryLedgerRepository:
    """Provide isolated in-memory ledger repository."""
    return InMemoryLedgerRepository()
