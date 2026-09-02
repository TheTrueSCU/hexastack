![hexastack-core](../../docs/assets/static/logos/packages/hexastack_core.png)

# hexastack-core

> The foundational kernel of Hexastack: dependency injection, abstract ports, domain abstractions, configuration registry, and the modular bootstrap lifecycle.

[![PyPI: hexastack-core](https://img.shields.io/pypi/v/hexastack-core.svg)](https://pypi.org/project/hexastack-core/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://codecov.io/github/TheTrueSCU/hexastack/graph/badge.svg?component=hexastack_core)](https://codecov.io/github/TheTrueSCU/hexastack)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](../../LICENSE)
---

## 1. Overview & Capabilities

`hexastack-core` serves as the zero-dependency (excluding `pydantic` and `rodi`) microkernel for all Hexastack packages. It establishes:

- **Dependency Injection Engine**: Powered by `rodi`, managing service lifecycles (singleton, scoped, transient).
- **Distributed & Persistent Cache Adapters**: `CachePort` and `AsyncCachePort` with in-memory (`InMemoryCache`, `AsyncInMemoryCache`), distributed Redis/Valkey (`RedisCacheAdapter`, `AsyncRedisCacheAdapter`), and persistent L2 filesystem storage (`DiskCacheAdapter`, `AsyncDiskCacheAdapter`).
- **High-Availability Primitives & Locks**: `LockPort` and `AsyncLockPort` (reentrant in-memory, OS `FileLockAdapter`, and distributed `RedisLockAdapter`) and `LeaderElectionPort` / `AsyncLeaderElectionPort` (single-process and distributed Redis lease coordination).
- **Core Domain Primitives**: Generic `Result[T, E]`, generic types, and standard exception hierarchies (`HexastackError`, `ConfigurationError`, `MissingDependencyError`, `LockError`, `LeaderElectionError`).
- **Core Port Contracts**: Standard abstract protocols and ABCs for repositories (`Repository[E, ID]`), unit of work (`UnitOfWork`), caching (`CachePort`), distributed locks (`LockPort`), leader election (`LeaderElectionPort`), logging (`LoggerPort`), presenters (`PresenterPort`), feature flags (`FeatureFlagPort`), and bootstrappers (`BootstrapperPort`).
- **Configuration & Type Registries**: Type-safe Pydantic configuration parsing from TOML (`ConfigRegistry`) and generic type registries (`GenericTypeRegistry`).
- **Three-Phase Bootstrap Engine**: Deterministic orchestration of Phase 1 config registration, Phase 2 container assembly, and Phase 3 reflective scanning.
- **Testing & Quality Toolkit**:
  - `assert_clean_architecture(...)`: Hexagonal architecture boundary verification powered by `pytest-archon`.
  - `create_test_runtime(...)`: Lightweight in-memory DI test harness and doubles (`TestRuntime`).
  - `cqrs_strategy(...)`: Hypothesis property-based fuzzing strategy generator for Pydantic/dataclass CQRS models.
  - Feature flag testing: `@parametrize_flags`, `flag_scope`, `@require_feature`, and `@require_extra`.
- **Context Utilities**: Async-safe correlation ID and context variable management (`get_correlation_id`, `set_correlation_id`, `UserContext`).

---

## 2. Package Anatomy & Key Components

```
hexastack_core/
├── domain/          # Result[T, E], HexastackError, Entity, ValueObject, EvaluationContext
├── ports/           # Repository, UnitOfWork, BootstrapperPort, LoggerPort, CachePort, LockPort, LeaderElectionPort
├── adapters/        # InMemory, Redis, DiskCache, FileLock implementations
├── infra/           # Bootstrap engine, ConfigRegistry, GenericTypeRegistry, decorators
├── testing/         # assert_clean_architecture, create_test_runtime, cqrs_strategy, flag_scope, isolation
└── utils/           # Context variable utilities, reflection helpers
```

### Key Exports

| Category | Exports |
|---|---|
| **Bootstrap** | `bootstrap`, `BootstrapContext`, `BootstrapResult`, `scan_modules` |
| **Cache** | `CachePort`, `AsyncCachePort`, `InMemoryCache`, `AsyncInMemoryCache`, `RedisCacheAdapter`, `AsyncRedisCacheAdapter`, `DiskCacheAdapter`, `AsyncDiskCacheAdapter` |
| **Config** | `ConfigRegistry`, `HexastackConfig`, `HexastackCoreConfig`, `@config_section` |
| **Context** | `get_correlation_id`, `set_correlation_id`, `correlation_scope`, `UserContext` |
| **Domain** | `Result`, `Ok`, `Err`, `HexastackError`, `ConfigurationError`, `MissingDependencyError`, `EntityNotFoundError`, `LockError`, `LeaderElectionError` |
| **Feature Flags** | `EvaluationContext`, `FlagEvaluationDetails`, `InMemoryFeatureFlagAdapter`, `ConfigFeatureFlagAdapter` |
| **High Availability & Locks** | `LockPort`, `AsyncLockPort`, `InMemoryLock`, `AsyncInMemoryLock`, `FileLockAdapter`, `AsyncFileLockAdapter`, `RedisLockAdapter`, `AsyncRedisLockAdapter`, `LeaderElectionPort`, `AsyncLeaderElectionPort`, `SingleProcessLeaderElection`, `AsyncSingleProcessLeaderElection`, `RedisLeaderElectionAdapter`, `AsyncRedisLeaderElectionAdapter` |
| **Ports** | `BootstrapperPort`, `CachePort`, `AsyncCachePort`, `LockPort`, `AsyncLockPort`, `LeaderElectionPort`, `AsyncLeaderElectionPort`, `Repository`, `AsyncRepository`, `UnitOfWork`, `AsyncUnitOfWork`, `LoggerPort`, `PresenterPort`, `FeatureFlagPort` |
| **Registries** | `GenericTypeRegistry`, `ExceptionRegistry` |
| **Testing** | `assert_clean_architecture`, `create_test_runtime`, `TestRuntime`, `cqrs_strategy`, `faker_strategy`, `flag_scope`, `generate_synthetic_payload`, `isolate_registries`, `parametrize_flags`, `@require_extra`, `@require_feature`, `seeded_faker` |



---

## 3. Monorepo & Sibling Relationships

```mermaid
graph TD
    subgraph SiblingPackages ["Dependent Sibling Packages"]
        CQRS["hexastack-cqrs"]
        LOG["hexastack-logging"]
        DB["hexastack-db"]
        FASTAPI["hexastack-fastapi"]
        GRAPHQL["hexastack-graphql"]
        MCP["hexastack-mcp"]
        GRPC["hexastack-grpc"]
        CLI["hexastack-cli"]
        UMBRELLA["hexastack"]
    end

    subgraph CoreKernel ["hexastack-core"]
        DI["rodi.Container"]
        BOOT["Bootstrap Engine"]
        PORTS["Abstract Ports (UoW, Repo, Logger)"]
        CONF["ConfigRegistry"]
    end

    CQRS -->|implements BootstrapperPort, uses rodi| CoreKernel
    LOG -->|implements LoggerPort & BootstrapperPort| CoreKernel
    DB -->|implements Repository & UnitOfWork ports| CoreKernel
    FASTAPI -->|implements BootstrapperPort, consumes DI| CoreKernel
    GRAPHQL -->|implements BootstrapperPort, consumes DI| CoreKernel
    MCP -->|implements BootstrapperPort, consumes DI| CoreKernel
    GRPC -->|implements BootstrapperPort, consumes DI| CoreKernel
    CLI -->|implements BootstrapperPort, consumes DI| CoreKernel
    UMBRELLA -->|orchestrates bootstrap| CoreKernel
```

### Explicit Dependencies (Direct)
- `pydantic>=2.13.4`: Schema validation and config parsing.
- `rodi>=2.1.0`: Fast, lightweight dependency injection container.

### Implied / Behavioral Relationships (DI-Mediated)
- **Provides Ports**: Defines `UnitOfWorkPort` and `Repository` implemented by `hexastack-db`.
- **Provides Telemetry Contract**: Defines `LoggerPort` implemented by `hexastack-logging`.
- **Provides Bootstrap Framework**: All siblings expose extension entry points implementing `BootstrapperPort`.

---

## 4. Installation

```bash
# Standalone installation
pip install hexastack-core

# Via umbrella package
pip install hexastack
```

---

## 5. Configuration Reference

Configuration schemas are registered under `[hexastack]`:

```toml
[hexastack]
app_name = "my-application"
environment = "production" # "development", "staging", "production", "test"
debug = false
```

---

## 6. Quickstart Example

```python
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.bootstrap import BootstrapperPort, BootstrapContext
from hexastack_core.domain.result import Ok, Err, Result


# 1. Implement a custom extension
class ServiceBootstrapper(BootstrapperPort):
    name = "custom_service"
    order = 10

    def configure(self, context: BootstrapContext) -> None:
        context.container.add_instance("Service Configured", declared_class=str)


# 2. Run deterministic bootstrap
result = bootstrap(bootstrappers=[ServiceBootstrapper()], auto_discover=False)
value = result.container.get(str)
print(value)  # "Service Configured"
```
