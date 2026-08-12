import types
from typing import Any

from hexastack_core.adapters.logging import InMemoryLogger
from hexastack_core.adapters.unit_of_work.in_memory import InMemoryUnitOfWork
from hexastack_core.domain import Command, Generic
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.logging import LoggingPort
from hexastack_core.ports.unit_of_work import UnitOfWorkPort
from hexastack_cqrs.infra.bootstrap import (
    CqrsBootstrapper,
    bootstrap_cqrs,
)
from hexastack_cqrs.infra.decorators import command_handler, presenter
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_logging.infra.bootstrap import LoggingBootstrapper
from rodi import Container


class CreateAccount(Command):
    account_id: str
    owner: str


class AccountDTO(Generic):
    account_id: str
    owner: str


class AccountService:
    def format_owner(self, owner: str) -> str:
        return f"Verified: {owner}"


@command_handler(CreateAccount)
class CreateAccountHandler:
    def __init__(self, service: AccountService, logger: LoggingPort) -> None:
        self.service = service
        self.logger = logger

    def __call__(self, cmd: CreateAccount) -> AccountDTO:
        self.logger.info(f"Creating account {cmd.account_id}")
        return AccountDTO(
            account_id=cmd.account_id,
            owner=self.service.format_owner(cmd.owner),
        )


@presenter(AccountDTO, "json")
class AccountJsonPresenter:
    def present(self, instance: Generic) -> Any | None:
        if isinstance(instance, AccountDTO):
            return {"account_id": instance.account_id, "owner": instance.owner}
        return None


def test_bootstrap_default():
    result = bootstrap_cqrs()

    assert result.pipeline is not None
    assert result.container is not None
    assert result.handler_registry is not None
    assert result.command_registry is not None
    assert result.query_registry is not None


def test_bootstrap_with_di_and_autodiscovery():
    logger = InMemoryLogger()
    container = Container()
    container.add_instance(logger, declared_class=LoggingPort)
    container.register(AccountService)

    # Create dummy module containing handlers and presenters
    mod = types.ModuleType("account_mod")
    members = {
        "AccountService": AccountService,
        "CreateAccountHandler": CreateAccountHandler,
        "AccountJsonPresenter": AccountJsonPresenter,
    }
    for name, member in members.items():
        setattr(mod, name, member)

    result = bootstrap_cqrs(
        container=container,
        packages_to_scan=[mod],
    )

    # Execute discovered command with DI resolution
    res = result.pipeline.execute(
        CreateAccount(account_id="acc-1", owner="Alice"),
        output_format="json",
    )

    assert res == {"account_id": "acc-1", "owner": "Verified: Alice"}
    assert len(logger.entries) > 0
    assert any("Creating account acc-1" in entry.message for entry in logger.entries)


def test_bootstrap_with_logging_extension():
    res = bootstrap(
        bootstrappers=[LoggingBootstrapper(), CqrsBootstrapper()],
        auto_discover=False,
    )

    assert LoggingPort in res.container
    assert ExecutionPipeline in res.container

    pipeline: ExecutionPipeline = res.get("pipeline")
    assert pipeline is not None

    handler_reg = res.container.resolve(HandlerRegistry)
    handler_reg.register(
        CreateAccount,
        lambda cmd: AccountDTO(account_id=cmd.account_id, owner=cmd.owner),
    )

    account = pipeline.execute(CreateAccount(account_id="acc-ext", owner="Eve"))
    assert account.account_id == "acc-ext"


def test_bootstrap_with_uow_and_ordered_middleware():
    logger = InMemoryLogger()
    uow = InMemoryUnitOfWork()
    container = Container()
    container.add_instance(logger, declared_class=LoggingPort)
    container.register(AccountService)
    container.add_instance(uow, declared_class=UnitOfWorkPort)

    mod = types.ModuleType("account_uow_mod")
    members = {
        "AccountService": AccountService,
        "CreateAccountHandler": CreateAccountHandler,
    }
    for name, member in members.items():
        setattr(mod, name, member)

    result = bootstrap_cqrs(
        container=container,
        packages_to_scan=[mod],
    )

    res = result.pipeline.execute(CreateAccount(account_id="acc-2", owner="Bob"))
    assert isinstance(res, AccountDTO)
    assert uow.committed is True
    assert uow.commit_count == 1
