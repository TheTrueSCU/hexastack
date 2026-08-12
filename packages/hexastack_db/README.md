# hexastack-db

> SQLAlchemy 2.0+ persistence layer, generic repositories, Unit of Work, declarative mixins, and Alembic migrations for Hexastack.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)

---

## 1. Overview & Capabilities

`hexastack-db` provides a robust, decoupled database layer supporting both synchronous and asynchronous workflows:

- **Generic Repositories**: `SqlAlchemyRepository[T, ID]` and `AsyncSqlAlchemyRepository[T, ID]` implementing `Repository[E, ID]` and `AsyncRepository[E, ID]`.
- **Unit of Work**: `SqlAlchemyUnitOfWork` and `AsyncSqlAlchemyUnitOfWork` providing contextual transaction boundaries (`commit()`, `rollback()`).
- **Declarative Base & Mixins**:
  - `HexastackBase`: Shared `DeclarativeBase` for unified metadata management across applications and migration autogen.
  - `UuidPrimaryKeyMixin`: Portable Python-side `uuid4()` stored as a 36-character string primary key.
  - `TimestampMixin`: Automatic UTC `created_at` and `updated_at` timestamps.
- **Alembic Migration Engine**: Programmatic migration execution (`upgrade`, `downgrade`, `revision`, `current`, `history`, `stamp`) and CLI integration without requiring manual `alembic.ini` authoring.
- **Auto Table Creation**: Schema discovery and `create_all()` execution on bootstrap via `register_metadata()`.

---

## 2. Package Anatomy & Key Components

```
hexastack_db/
├── domain/          # DatabaseError, EntityNotFoundError, UniqueConstraintViolationError
├── adapters/        # SqlAlchemyRepository, AsyncSqlAlchemyRepository, SqlAlchemyUnitOfWork, AsyncSqlAlchemyUnitOfWork
└── infra/
    ├── bootstrap.py # DatabaseBootstrapper (order=15)
    ├── config.py    # HexastackDatabaseConfig
    ├── engine.py    # Engine and sessionmaker factory functions
    ├── mixins.py    # HexastackBase, UuidPrimaryKeyMixin, TimestampMixin
    ├── migrations.py# Alembic migration helpers
    └── registries/  # metadata.py (register_metadata, get_registered_metadata)
```

### Key Exports

| Category | Exports |
|---|---|
| **Repositories** | `SqlAlchemyRepository`, `AsyncSqlAlchemyRepository` |
| **Unit of Work** | `SqlAlchemyUnitOfWork`, `AsyncSqlAlchemyUnitOfWork` |
| **Mixins & Base** | `HexastackBase`, `UuidPrimaryKeyMixin`, `TimestampMixin` |
| **Migrations** | `init_migrations`, `get_alembic_config`, `run_upgrade`, `run_downgrade`, `run_revision`, `run_current`, `run_history`, `stamp` |
| **Registries** | `register_metadata`, `get_registered_metadata`, `clear_metadata_registry` |
| **Bootstrap** | `DatabaseBootstrapper` (order=15), `HexastackDatabaseConfig` |

---

## 3. Monorepo & Sibling Relationships

```mermaid
graph TD
    subgraph SiblingConsumers ["Sibling Consumers"]
        CQRS["hexastack-cqrs (UnitOfWorkMiddleware)"]
        FASTAPI["hexastack-fastapi (DbSessionMiddleware)"]
        CLI["hexastack (hexastack db <cmd>)"]
    end

    subgraph DatabasePackage ["hexastack-db"]
        BOOT["DatabaseBootstrapper (order=15)"]
        UOW["SqlAlchemyUnitOfWork / AsyncSqlAlchemyUnitOfWork"]
        ENG["Engine & sessionmaker"]
        MIGR["Alembic Migration Engine"]
    end

    subgraph CoreContracts ["hexastack-core"]
        UOW_PORT["UnitOfWorkPort"]
        REPO_PORT["RepositoryPort"]
    end

    BOOT --> UOW
    BOOT --> ENG
    UOW -->|implements| UOW_PORT

    CQRS -. consumes UnitOfWorkPort from DI .-> UOW
    FASTAPI -. consumes sessionmaker from DI .-> ENG
    CLI -. invokes migration helpers .-> MIGR
```

### Explicit Dependencies (Direct)
- `hexastack-core`: Core ports (`UnitOfWorkPort`, `Repository`), exception types, and DI container.
- `sqlalchemy>=2.0.38`: Core ORM and SQL toolkit.

### Implied / Behavioral Relationships (DI-Mediated)
- **Unit of Work Binding**: Binds `UnitOfWorkPort` into the DI container at `order=15` (before CQRS `order=20`), allowing `UnitOfWorkMiddleware` to manage transactions automatically.
- **Session Injection**: Injects `sessionmaker` / `async_sessionmaker` into DI, which `hexastack-fastapi` resolves in `DbSessionMiddleware` without requiring a direct package dependency.
- **Migration CLI Integration**: The `hexastack` umbrella package exposes CLI subcommands (`hexastack db init/upgrade/revision/...`) backed by `hexastack_db.infra.migrations`.

### Optional Integrations (Extras)
- `[sqlite]`: Installs `aiosqlite>=0.20.0` for async SQLite support.
- `[postgresql]`: Installs `asyncpg>=0.30.0` and `psycopg[binary]>=3.2.0`.
- `[migrations]`: Installs `alembic>=1.13.0` for migration commands and autogeneration.
- `[all]`: Installs all drivers and Alembic.

---

## 4. Installation

```bash
# Standalone install with SQLite async support
pip install "hexastack-db[sqlite]"

# Standalone with PostgreSQL and Alembic migrations
pip install "hexastack-db[postgresql,migrations]"

# Via umbrella package
pip install "hexastack[db]"
```

---

## 5. Configuration Reference

```toml
[hexastack.database]
url = "sqlite:///app.db" # "postgresql+asyncpg://user:pass@localhost:5432/dbname"
async_mode = false # Set to true for async engine & sessions
auto_create_tables = false # Runs create_all() on registered metadata at bootstrap
echo = false # Enables raw SQLAlchemy SQL logging
pool_size = 5
max_overflow = 10
pool_timeout = 30
pool_recycle = 1800
```

---

## 6. Quickstart Example

```python
from sqlalchemy.orm import Mapped, mapped_column
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.unit_of_work import UnitOfWorkPort
from hexastack_db.infra.mixins import HexastackBase, UuidPrimaryKeyMixin, TimestampMixin
from hexastack_db.infra.registries.metadata import register_metadata
from hexastack_db.adapters.repository import SqlAlchemyRepository


# 1. Define Model
class UserRecord(UuidPrimaryKeyMixin, TimestampMixin, HexastackBase):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(unique=True)


register_metadata(HexastackBase.metadata)

# 2. Bootstrap with auto-table creation
runtime = bootstrap(
    config_overrides={
        "database": {
            "url": "sqlite:///:memory:",
            "auto_create_tables": True,
        }
    }
)

# 3. Use Unit of Work and Repository
uow = runtime.container.get(UnitOfWorkPort)
with uow:
    repo = SqlAlchemyRepository(session=uow.session, model_cls=UserRecord)
    user = UserRecord(email="alice@hexastack.dev")
    repo.add(user)
    uow.commit()

print(f"Created user {user.id} at {user.created_at}")
```
