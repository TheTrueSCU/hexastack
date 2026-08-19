from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from rodi import Container

from hexastack_core.domain import Command, Generic, Query
from hexastack_core.ports.presenter import PresenterPort
from hexastack_cqrs.adapters.buses.command.synchronous import (
    SynchronousCommandBus,
)
from hexastack_cqrs.adapters.buses.event.synchronous import (
    SynchronousEventBus,
)
from hexastack_cqrs.adapters.buses.query.synchronous import (
    SynchronousQueryBus,
)
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.command import CommandRegistry
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry
from hexastack_cqrs.infra.registries.query import QueryRegistry
from hexastack_fastapi.adapters.routing import CqrsRouter


class RegisterUser(Command):
    user_id: str
    username: str


class GetUser(Query):
    user_id: str


class UserDTO(Generic):
    user_id: str
    username: str


def test_cqrs_router_command_and_query():
    handler_reg = HandlerRegistry()
    presenter_reg = PresenterRegistry()

    # Handlers
    handler_reg.register(
        RegisterUser,
        lambda cmd: UserDTO(user_id=cmd.user_id, username=cmd.username),
    )
    handler_reg.register(
        GetUser,
        lambda qry: UserDTO(user_id=qry.user_id, username=f"user_{qry.user_id}"),
    )

    # Presenter
    class UserJsonPresenter(PresenterPort):
        def present(self, instance: Generic) -> Any:
            if isinstance(instance, UserDTO):
                return {"id": instance.user_id, "name": instance.username}
            return None

    presenter_reg.register(UserDTO, "json", UserJsonPresenter())

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=presenter_reg,
    )

    router = CqrsRouter(prefix="/users")
    router.add_command(
        "/register",
        RegisterUser,
        method="POST",
        status_code=201,
        output_format="json",
        summary="Custom Register Summary",
    )
    # Also test default method / status_code and summary generation
    router.add_command(
        "/register-default",
        RegisterUser,
    )
    router.add_query(
        "/get",
        GetUser,
        method="GET",
        output_format="json",
        summary="Custom Get Summary",
    )
    # Also test POST query route
    router.add_query(
        "/get-post",
        GetUser,
        method="POST",
        output_format="json",
    )

    app = FastAPI()
    app.state.pipeline = pipeline
    app.include_router(router)

    client = TestClient(app)

    # 1. Execute Command via POST with custom status code
    cmd_res = client.post(
        "/users/register", json={"user_id": "u-1", "username": "Alice"}
    )
    assert cmd_res.status_code == 201
    assert cmd_res.json() == {"id": "u-1", "name": "Alice"}

    # Execute Command via default registration
    cmd_res_def = client.post(
        "/users/register-default", json={"user_id": "u-2", "username": "Bob"}
    )
    assert cmd_res_def.status_code == 200

    # 2. Execute Query via GET
    qry_res = client.get("/users/get?user_id=u-1")
    assert qry_res.status_code == 200
    assert qry_res.json() == {"id": "u-1", "name": "user_u-1"}

    # Execute Query via POST
    qry_post_res = client.post("/users/get-post", json={"user_id": "u-1"})
    assert qry_post_res.status_code == 200
    assert qry_post_res.json() == {"id": "u-1", "name": "user_u-1"}


def test_cqrs_router_feature_flag_gated():
    from rodi import Container

    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.ports.feature_flags import FeatureFlagPort

    handler_reg = HandlerRegistry()
    handler_reg.register(
        RegisterUser,
        lambda cmd: UserDTO(user_id=cmd.user_id, username=cmd.username),
    )

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=PresenterRegistry(),
    )

    flags = InMemoryFeatureFlagAdapter({"features.api.registration": False})
    container = Container()
    container.add_instance(flags, declared_class=FeatureFlagPort)

    router = CqrsRouter()
    router.add_command(
        "/register-gated", RegisterUser, feature_flag="features.api.registration"
    )

    app = FastAPI()
    app.state.container = container
    app.state.pipeline = pipeline
    app.include_router(router)

    client = TestClient(app)

    # 1. Disabled returns 404
    res_disabled = client.post(
        "/register-gated", json={"user_id": "u-gated", "username": "Gated"}
    )
    assert res_disabled.status_code == 404

    # 2. Enabling dynamically unlocks endpoint
    flags.set_flag("features.api.registration", True)
    res_enabled = client.post(
        "/register-gated", json={"user_id": "u-gated", "username": "Gated"}
    )
    assert res_enabled.status_code == 200


def test_cqrs_router_openapi_conformance_with_schemathesis():
    from hexastack_fastapi.adapters.dependencies import (
        check_openapi_conformance,
        create_test_client,
    )

    handler_reg = HandlerRegistry()
    presenter_reg = PresenterRegistry()

    handler_reg.register(
        RegisterUser,
        lambda cmd: UserDTO(user_id=cmd.user_id, username=cmd.username),
    )
    handler_reg.register(
        GetUser,
        lambda qry: UserDTO(user_id=qry.user_id, username=f"user_{qry.user_id}"),
    )

    class UserJsonPresenter(PresenterPort):
        def present(self, instance: Generic) -> Any:
            if isinstance(instance, UserDTO):
                return {"id": instance.user_id, "name": instance.username}
            return None

    presenter_reg.register(UserDTO, "json", UserJsonPresenter())

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=presenter_reg,
    )

    router = CqrsRouter()
    router.add_command("/users", RegisterUser, status_code=201)
    router.add_query("/users/{user_id}", GetUser)

    app = FastAPI()
    container = Container()
    app.state.container = container
    app.state.pipeline = pipeline
    app.include_router(router)

    # 1. Test Client with initial flag injection
    client = create_test_client(app, flags={"api.enabled": True})
    assert client.get("/openapi.json").status_code == 200

    # 2. Automated Schemathesis conformance test
    check_openapi_conformance(app, validate_schema=True)
