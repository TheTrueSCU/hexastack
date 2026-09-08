"""Property-based fuzzing tests for double-entry financial ledger invariants."""

from __future__ import annotations

from decimal import Decimal
from hypothesis import given, strategies as st
import pytest

from financial_ledger.domain.exceptions import UnbalancedTransactionError
from financial_ledger.domain.models import (
    Account,
    EntryDirection,
    JournalTransaction,
    TransactionEntry,
)


@given(
    amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000000.00"), places=2),
)
def test_fuzz_balanced_transfer_conservation_of_money(amount: Decimal):
    """Conservation of Money Property: Total money before transaction == Total money after transaction."""
    initial_src = Decimal("2000000.00")
    initial_dst = Decimal("1000000.00")

    src_acc = Account(account_id="src", balance=initial_src)
    dst_acc = Account(account_id="dst", balance=initial_dst)

    total_before = src_acc.balance + dst_acc.balance

    debit_entry = TransactionEntry(account_id="src", direction=EntryDirection.DEBIT, amount=amount)
    credit_entry = TransactionEntry(account_id="dst", direction=EntryDirection.CREDIT, amount=amount)

    tx = JournalTransaction(reference="FUZZ-TX", description="Fuzz transfer", entries=[debit_entry, credit_entry])
    assert tx.reference == "FUZZ-TX"

    src_acc.apply_entry(debit_entry)
    dst_acc.apply_entry(credit_entry)

    total_after = src_acc.balance + dst_acc.balance

    assert total_before == total_after
    assert src_acc.balance == initial_src - amount
    assert dst_acc.balance == initial_dst + amount


@given(
    debit_amount=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000.00"), places=2),
    credit_diff=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("100.00"), places=2),
)
def test_fuzz_unbalanced_transactions_always_fail(debit_amount: Decimal, credit_diff: Decimal):
    """Property: Any transaction with debits != credits MUST raise UnbalancedTransactionError."""
    credit_amount = debit_amount + credit_diff

    entries = [
        TransactionEntry(account_id="acc-1", direction=EntryDirection.DEBIT, amount=debit_amount),
        TransactionEntry(account_id="acc-2", direction=EntryDirection.CREDIT, amount=credit_amount),
    ]

    with pytest.raises(UnbalancedTransactionError):
        JournalTransaction(reference="FUZZ-UNBALANCED", description="Unbalanced", entries=entries)
