import types

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
    assert bootstrapper.name == "fastapi"
    assert bootstrapper.order == 30

    bootstrapper.register_config(reg)

    assert "fastapi" in reg
    assert reg.get("fastapi") == HexastackFastApiConfig


def test_meta_bootstrap_with_fastapi_and_autodiscovery():
    mod = types.ModuleType("sample_greet_module")
    mod.__dict__["GreetUser"] = GreetUser
    mod.__dict__["GreetUserHandler"] = GreetUserHandler

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
    assert result.properties.get("app") is app

    # 2. Executing autodiscovered route via TestClient
    client = TestClient(app)
    res = client.post("/greet/hello", json={"name": "Hexastack"})
    assert res.status_code == 200
    assert res.json() == {"message": "Hello, Hexastack!"}
