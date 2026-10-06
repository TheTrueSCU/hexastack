"""In-memory thread-safe ledger and account storage adapters."""

from __future__ import annotations

import copy
import threading

from financial_ledger.domain.exceptions import ConcurrencyConflictError
from financial_ledger.domain.models import Account, JournalTransaction, TransactionEntry
from financial_ledger.ports.repositories import (
    AccountRepositoryPort,
    LedgerRepositoryPort,
)

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
        """Persist or update an account with optimistic concurrency validation.

        Args:
            account: The account entity to save.

        Raises:
            ConcurrencyConflictError: If the persisted version is greater than the update version.

        Notes/Architectural Intent:
            Enforces optimistic concurrency checks under thread safety lock.
        """
        with self._lock:
            existing = self._storage.get(account.account_id)
            if existing is not None and existing.version >= account.version:
                raise ConcurrencyConflictError(
                    f"Optimistic concurrency conflict on account '{account.account_id}': "
                    f"persisted version is {existing.version}, update has version {account.version}."
                )
            self._storage[account.account_id] = copy.deepcopy(account)

    def save_all(self, accounts: list[Account]) -> None:
        """Persist multiple accounts atomically with preflight optimistic concurrency validation.

        Args:
            accounts: Sequence of accounts to save atomically.

        Raises:
            ConcurrencyConflictError: If any account fails optimistic concurrency validation.

        Notes/Architectural Intent:
            Preflights all accounts under the lock before modifying state to ensure all-or-nothing atomicity.
        """
        with self._lock:
            for account in accounts:
                existing = self._storage.get(account.account_id)
                if existing is not None and existing.version >= account.version:
                    raise ConcurrencyConflictError(
                        f"Optimistic concurrency conflict on account '{account.account_id}': "
                        f"persisted version is {existing.version}, update has version {account.version}."
                    )
            for account in accounts:
                self._storage[account.account_id] = copy.deepcopy(account)

    def get_by_id(self, account_id: str) -> Account | None:
        """Retrieve an account by its unique identifier.

        Args:
            account_id: Unique account identifier.

        Returns:
            The account entity if found, otherwise None.

        Notes/Architectural Intent:
            Returns a deep copy to prevent mutation outside transaction boundaries.
        """
        with self._lock:
            acc = self._storage.get(account_id)
            return copy.deepcopy(acc) if acc is not None else None

    def list_all(self) -> list[Account]:
        """List all accounts currently stored in memory.

        Returns:
            List of deep-copied account entities.

        Notes/Architectural Intent:
            Isolated snapshot list for query operations.
        """
        with self._lock:
            return [copy.deepcopy(acc) for acc in self._storage.values()]


class InMemoryLedgerRepository(LedgerRepositoryPort):
    """In-memory repository adapter for immutable journal transactions."""

    def __init__(self) -> None:
        self._transactions: dict[str, JournalTransaction] = {}
        self._account_entries: dict[str, list[TransactionEntry]] = {}
        self._lock = threading.Lock()

    def save_transaction(self, transaction: JournalTransaction) -> None:
        """Persist an immutable journal transaction idempotently.

        Args:
            transaction: Balanced journal transaction to record.

        Raises:
            ConcurrencyConflictError: If a transaction with the same ID exists with different contents.

        Notes/Architectural Intent:
            Transactions are append-only and idempotent; existing transaction IDs are skipped if identical.
        """
        with self._lock:
            if transaction.transaction_id in self._transactions:
                existing_tx = self._transactions[transaction.transaction_id]
                if (
                    existing_tx.reference != transaction.reference
                    or existing_tx.entries != transaction.entries
                ):
                    raise ConcurrencyConflictError(
                        f"Transaction '{transaction.transaction_id}' already exists with different contents."
                    )
                # Idempotent replay of identical transaction
                return
            self._transactions[transaction.transaction_id] = copy.deepcopy(transaction)
            for entry in transaction.entries:
                if entry.account_id not in self._account_entries:
                    self._account_entries[entry.account_id] = []
                self._account_entries[entry.account_id].append(copy.deepcopy(entry))

    def get_transaction(self, transaction_id: str) -> JournalTransaction | None:
        """Retrieve a journal transaction by ID.

        Args:
            transaction_id: Unique transaction ID.

        Returns:
            The journal transaction if found, else None.

        Notes/Architectural Intent:
            Deep copy ensures immutability of the returned record.
        """
        with self._lock:
            tx = self._transactions.get(transaction_id)
            return copy.deepcopy(tx) if tx is not None else None

    def get_entries_for_account(self, account_id: str) -> list[TransactionEntry]:
        """Retrieve all transaction entries associated with a specific account.

        Args:
            account_id: The account identifier.

        Returns:
            List of transaction entries.

        Notes/Architectural Intent:
            Provides ledger audit trail per account.
        """
        with self._lock:
            entries = self._account_entries.get(account_id, [])
            return [copy.deepcopy(e) for e in entries]
