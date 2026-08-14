from rodi import Container

from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_events.adapters.buses.in_memory import (
    InMemoryDistributedEventBus,
)
from hexastack_events.adapters.outbox.asyncio import AsyncioOutboxRelay
from hexastack_events.adapters.outbox.huey import HueyOutboxRelay
from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage
from hexastack_events.infra.bootstrap import EventsBootstrapper
from hexastack_events.infra.config import HexastackEventsConfig
from hexastack_events.infra.middleware import OutboxCaptureMiddleware
from hexastack_events.ports.buses import DistributedEventBusPort
from hexastack_events.ports.outbox import (
    OutboxRelayPort,
    OutboxStoragePort,
)


def test_events_bootstrapper_attributes():
    bootstrapper = EventsBootstrapper()
    assert bootstrapper.name == "events"
    assert bootstrapper.order == 22


def test_events_bootstrapper_configuration_asyncio():
    bootstrapper = EventsBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    storage = container.resolve(OutboxStoragePort)
    assert isinstance(storage, InMemoryOutboxStorage)

    bus = container.resolve(DistributedEventBusPort)
    assert isinstance(bus, InMemoryDistributedEventBus)

    relay = container.resolve(OutboxRelayPort)
    assert isinstance(relay, AsyncioOutboxRelay)

    middleware = container.resolve(OutboxCaptureMiddleware)
    assert isinstance(middleware, OutboxCaptureMiddleware)

    # Properties
    assert ctx.properties["events_config"].relay_mode == "asyncio"
    assert ctx.properties["outbox_storage"] is storage
    assert ctx.properties["distributed_bus"] is bus
    assert ctx.properties["outbox_relay"] is relay


def test_events_bootstrapper_configuration_huey():
    bootstrapper = EventsBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    cfg = HexastackEventsConfig(relay_mode="huey", batch_size=25)
    container.add_instance(cfg, declared_class=HexastackEventsConfig)

    custom_storage = InMemoryOutboxStorage()
    container.add_instance(custom_storage, declared_class=OutboxStoragePort)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    relay = container.resolve(OutboxRelayPort)
    assert isinstance(relay, HueyOutboxRelay)
    assert relay._batch_size == 25
    assert ctx.properties["outbox_storage"] is custom_storage


def test_events_bootstrapper_configuration_disabled_relay():
    bootstrapper = EventsBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    cfg = HexastackEventsConfig(relay_mode="disabled")
    container.add_instance(cfg, declared_class=HexastackEventsConfig)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    # Relay should not be registered when disabled
    assert OutboxRelayPort not in container
    assert "outbox_relay" not in ctx.properties
