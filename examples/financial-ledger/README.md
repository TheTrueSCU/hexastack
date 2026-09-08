# 🏦 Financial Ledger Service (`examples/financial-ledger`)

> Production-grade Double-Entry Financial Ledger Microservice built with **[Hexastack](https://github.com/TheTrueSCU/hexastack)**.

---

## 1. Overview & Architectural Highlights

The **Financial Ledger Service** is a reference architecture microservice demonstrating how Hexastack guarantees **strict consistency**, **double-entry mathematical invariants**, and **pure domain isolation** for mission-critical financial applications.

- **Double-Entry Accounting Invariant**: Enforces $\sum \text{Debits} = \sum \text{Credits}$ at the domain level before persistence.
- **Exact Decimal Arithmetic**: Uses Python `Decimal` everywhere to eliminate IEEE 754 floating-point rounding errors.
- **Strict Hexagonal Architecture**: Zero-framework domain models isolated behind abstract repository ports.
- **CQRS Execution Pipeline**: Decoupled Command (`TransferMoneyCommand`, `RecordTransactionCommand`, `CreateAccountCommand`) and Query (`GetAccountBalanceQuery`, `ListLedgerEntriesQuery`) execution with automatic dependency injection via Rodi.
- **Multi-Adapter Driving Ports**: Exposed via FastAPI REST and Typer CLI.
- **Property-Based Fuzzing**: Comprehensive Hypothesis test suite proving money conservation and invariant enforcement across millions of randomized inputs.

---

## 2. Directory Layout

```text
examples/financial-ledger/
├── .importlinter                 # Strict layer isolation and adapter independence rules
├── pyproject.toml                # Project metadata, scripts, and quality gate configs
├── src/financial_ledger/
│   ├── domain/                   # Pure Domain Core (Zero External Dependencies)
│   │   ├── models.py             # Account, TransactionEntry, JournalTransaction, Invariants
│   │   ├── commands.py           # CQRS Commands, Queries, and Response DTOs
│   │   └── exceptions.py         # Domain errors (InsufficientFundsError, UnbalancedTransactionError)
│   ├── ports/                    # Abstract Secondary Interfaces
│   │   └── repositories.py       # AccountRepositoryPort, LedgerRepositoryPort
│   ├── adapters/
│   │   ├── driven/               # Outbound Infrastructure Adapters
│   │   │   └── database.py       # Thread-safe in-memory account & ledger storage
│   │   └── driving/              # Inbound Driving Adapters
│   │       ├── cli.py            # Typer CLI commands
│   │       └── http.py           # FastAPI REST API endpoints
│   └── infra/                    # Application Kernel & Assembly
│       ├── bootstrap.py          # Rodi DI container & Hexastack bootstrapper
│       ├── cli.py                # CLI runner entrypoint
│       ├── config.py             # AppConfig settings
│       └── handlers.py           # CQRS Command and Query Handlers
└── tests/
    ├── conftest.py               # Shared pytest fixtures
    ├── hypothesis/               # Property-based fuzzing tests
    │   └── test_domain_fuzz.py
    └── unit/                     # Unit and integration test suites
        ├── test_domain.py
        └── test_infra.py
```

---

## 3. Running Tests & Quality Gates

```bash
# 1. Run Unit and Property-Based Fuzzing Tests (with >= 90% coverage enforcement)
PYTHONPATH=examples/financial-ledger/src uv run pytest examples/financial-ledger/tests --cov=examples/financial-ledger/src/financial_ledger

# 2. Verify Hexagonal Layer Contracts with Import-Linter
PYTHONPATH=examples/financial-ledger/src uv run lint-imports --config=examples/financial-ledger/.importlinter
```
