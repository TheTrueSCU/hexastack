"""In-memory thread-safe ledger and account storage adapters."""

from __future__ import annotations

import copy
import threading
from typing import Optional

from financial_ledger.domain.models import Account, JournalTransaction, TransactionEntry
from financial_ledger.ports.repositories import AccountRepositoryPort, LedgerRepositoryPort

__all__ = [
    "InMemoryAccountRepository",
    "InMemoryLedgerRepository",
]


class InMemoryAccountRepository(AccountRepositoryPort):
    """In-memory repository adapter for Account entities."""

    def __init__(self) -> None:
        self._storage: dict[str, Account] = {}
        self._lock = threading.Lock()

    def save(self, account: Account) -> None:
        with self._lock:
            self._storage[account.account_id] = copy.deepcopy(account)

    def get_by_id(self, account_id: str) -> Optional[Account]:
        with self._lock:
            acc = self._storage.get(account_id)
            return copy.deepcopy(acc) if acc is not None else None

    def list_all(self) -> list[Account]:
        with self._lock:
            return [copy.deepcopy(acc) for acc in self._storage.values()]


class InMemoryLedgerRepository(LedgerRepositoryPort):
    """In-memory repository adapter for immutable journal transactions."""

    def __init__(self) -> None:
        self._transactions: dict[str, JournalTransaction] = {}
        self._account_entries: dict[str, list[TransactionEntry]] = {}
        self._lock = threading.Lock()

    def save_transaction(self, transaction: JournalTransaction) -> None:
        with self._lock:
            self._transactions[transaction.transaction_id] = copy.deepcopy(transaction)
            for entry in transaction.entries:
                if entry.account_id not in self._account_entries:
                    self._account_entries[entry.account_id] = []
                self._account_entries[entry.account_id].append(copy.deepcopy(entry))

    def get_transaction(self, transaction_id: str) -> Optional[JournalTransaction]:
        with self._lock:
            tx = self._transactions.get(transaction_id)
            return copy.deepcopy(tx) if tx is not None else None

    def get_entries_for_account(self, account_id: str) -> list[TransactionEntry]:
        with self._lock:
            entries = self._account_entries.get(account_id, [])
            return [copy.deepcopy(e) for e in entries]
