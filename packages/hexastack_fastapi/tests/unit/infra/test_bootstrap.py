import types
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hexastack_core.domain import Command, Generic
from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_cqrs.infra.bootstrap import CqrsBootstrapper
from hexastack_cqrs.infra.decorators import command_handler
from hexastack_fastapi.infra.bootstrap import FastApiBootstrapper
from hexastack_fastapi.infra.config import HexastackFastApiConfig
from hexastack_fastapi.infra.decorators import api_command
from hexastack_logging.infra.bootstrap import LoggingBootstrapper


@api_command("/greet/hello", method="POST")
class GreetUser(Command):
    name: str


class GreetingDTO(Generic):
    message: str


@command_handler(GreetUser)
class GreetUserHandler:
    def __call__(self, cmd: GreetUser) -> GreetingDTO:
        return GreetingDTO(message=f"Hello, {cmd.name}!")


def test_fastapi_bootstrapper_registration():
    reg = ConfigRegistry()
    bootstrapper = FastApiBootstrapper()
    bootstrapper.register_config(reg)

    assert "fastapi" in reg
    assert reg.get("fastapi") == HexastackFastApiConfig


def test_meta_bootstrap_with_fastapi_and_autodiscovery():
    mod = types.ModuleType("sample_greet_module")
    cast(Any, mod).GreetUser = GreetUser
    cast(Any, mod).GreetUserHandler = GreetUserHandler

    result = bootstrap(
        bootstrappers=[
            LoggingBootstrapper(),
            CqrsBootstrapper(),
            FastApiBootstrapper(),
        ],
        packages_to_scan=[mod],
        auto_discover=False,
    )

    # 1. FastAPI app is present in container and result
    assert FastAPI in result.container
    app = result.get("app")
    assert isinstance(app, FastAPI)

    # 2. Test request execution & health checks in single-pass autodiscovered setup
    with TestClient(app) as client:
        # Health check
        h_res = client.get("/health")
        assert h_res.status_code == 200
        assert h_res.json()["status"] == "ok"

        # Autodiscovered endpoint dispatched directly to autodiscovered handler
        res = client.post("/greet/hello", json={"name": "Antigravity"})
        assert res.status_code == 200
        assert res.json() == {"message": "Hello, Antigravity!"}
        assert res.headers.get("x-correlation-id") is not None
