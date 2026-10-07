# Tutorial 8: Double-Entry Financial Ledger & Mathematical Invariants

In this tutorial, you will explore the **Financial Ledger Service** (`examples/financial-ledger`), a reference architecture demonstrating how **Hexastack** enforces **strict consistency**, **double-entry invariants**, and **pure domain isolation** for mission-critical financial systems.

By the end of this guide, you will understand:

- How to design pure Python double-entry accounting models with exact `Decimal` arithmetic.
- How to enforce the fundamental double-entry invariant ($\sum \text{Debits} = \sum \text{Credits}$) at the domain boundary.
- How CQRS Command and Query pipelines cleanly separate ledger mutations from balance and history queries.
- How to use **Hypothesis** property-based fuzzing to mathematically verify the **Law of Conservation of Money**.
- How **import-linter** guarantees zero leaking of infrastructure or database details into financial logic.

---

## 1. Domain Design: Double-Entry Principles & Invariants

Double-entry bookkeeping mandates that every financial transaction consists of at least two posting lines whose total debits exactly equal total credits:

$$ \sum \text{Debits} = \sum \text{Credits} $$

### Pure Domain Entities & Invariant Enforcement

In `src/financial_ledger/domain/models.py`, we define our immutable value objects and domain entities:

```python
from decimal import Decimal
from enum import StrEnum
from dataclasses import dataclass, field


class EntryDirection(StrEnum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


@dataclass(frozen=True)
class TransactionEntry:
    account_id: str
    direction: EntryDirection
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount <= Decimal("0.00"):
            raise InvalidAmountError(
                f"Entry amount must be strictly positive, got {self.amount}"
            )


@dataclass(frozen=True)
class JournalTransaction:
    reference: str
    description: str
    entries: Sequence[TransactionEntry]

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", tuple(self.entries))
        if len(self.entries) < 2:
            raise UnbalancedTransactionError(
                "A double-entry transaction requires at least two posting lines."
            )

        currencies = {e.currency for e in self.entries}
        for curr in sorted(currencies):
            curr_debits = sum(
                (
                    e.amount
                    for e in self.entries
                    if e.direction == EntryDirection.DEBIT and e.currency == curr
                ),
                start=Decimal("0.00"),
            )
            curr_credits = sum(
                (
                    e.amount
                    for e in self.entries
                    if e.direction == EntryDirection.CREDIT and e.currency == curr
                ),
                start=Decimal("0.00"),
            )

            if curr_debits != curr_credits:
                raise UnbalancedTransactionError(
                    f"Unbalanced double-entry transaction '{self.reference}' for currency '{curr}': "
                    f"total debits ({curr_debits}) != total credits ({curr_credits})"
                )
```

---

## 2. CQRS Commands, Handlers & Inverted Ports

Mutations and queries are decoupled into explicit CQRS messages in `src/financial_ledger/domain/commands.py`:

- **`CreateAccountCommand`**: Register a new ledger account.
- **`FreezeAccountCommand`**: Freeze an account to prevent any future debits/credits.
- **`TransferMoneyCommand`**: Execute a 2-legged transfer between accounts.
- **`RecordTransactionCommand`**: Record an arbitrary multi-legged balanced transaction (e.g. platform fee splits).
- **`GetAccountBalanceQuery`**: Query current balance and status.
- **`ListLedgerEntriesQuery`**: Retrieve historical posting lines.

### Handler Dependency Injection via Rodi

Handlers in `src/financial_ledger/infra/handlers.py` declare their port dependencies in the constructor and are auto-wired by Hexastack's Rodi container:

```python
@command_handler(TransferMoneyCommand)
class TransferMoneyHandler:
    def __init__(
        self,
        account_repo: AccountRepositoryPort,
        ledger_repo: LedgerRepositoryPort,
    ) -> None:
        self.account_repo = account_repo
        self.ledger_repo = ledger_repo

    def __call__(self, cmd: TransferMoneyCommand) -> TransferMoneyResponse:
        # Business logic: validate accounts, create balanced entries, apply & persist
        ...
```

---

## 3. Multi-Transport Driving Ports (FastAPI REST & Typer CLI)

The same CQRS pipeline is exposed simultaneously over REST and CLI without duplicating business logic:

### FastAPI REST Endpoints (`src/financial_ledger/adapters/driving/http.py`)

```python
@router.post("/transfers", summary="Transfer money between accounts")
def transfer_money(
    cmd: TransferMoneyCommand,
    pipeline: Annotated[ExecutionPipeline, Depends(get_pipeline)],
) -> TransferMoneyResponse:
    return pipeline.execute(cmd)
```

---

## 4. Property-Based Fuzzing with Hypothesis

How do we prove our financial ledger never loses a cent? We write property-based tests in `tests/hypothesis/test_domain_fuzz.py`:

```python
from hypothesis import given, strategies as st
from decimal import Decimal


@given(
    amount=st.decimals(
        min_value=Decimal("0.01"), max_value=Decimal("1000000.00"), places=2
    )
)
def test_fuzz_balanced_transfer_conservation_of_money(amount: Decimal):
    """Conservation of Money: Total ledger money before == Total ledger money after."""
    src_acc = Account(account_id="src", balance=Decimal("2000000.00"))
    dst_acc = Account(account_id="dst", balance=Decimal("1000000.00"))

    total_before = src_acc.balance + dst_acc.balance

    debit_entry = TransactionEntry(
        account_id="src", direction=EntryDirection.DEBIT, amount=amount
    )
    credit_entry = TransactionEntry(
        account_id="dst", direction=EntryDirection.CREDIT, amount=amount
    )

    src_acc.apply_entry(debit_entry)
    dst_acc.apply_entry(credit_entry)

    total_after = src_acc.balance + dst_acc.balance
    assert total_before == total_after
```

---

## 5. Architectural Guardrails with Import-Linter

The service enforces strict hexagonal layer boundaries via `examples/financial-ledger/.importlinter`:

```ini
[importlinter:contract:hexagonal-layers]
name = Hexagonal Architecture Layers
type = layers
containers = financial_ledger
layers =
    infra
    adapters
    ports
    domain
```

Run the linter to verify full compliance:

```bash
PYTHONPATH=examples/financial-ledger/src uv run lint-imports --config=examples/financial-ledger/.importlinter
```
