from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_events.adapters.buses.in_memory import (
    InMemoryDistributedEventBus,
)
from hexastack_events.adapters.outbox.asyncio import AsyncioOutboxRelay
from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage
from hexastack_events.infra.bootstrap import EventsBootstrapper
from hexastack_events.infra.config import HexastackEventsConfig
from hexastack_events.infra.middleware import OutboxCaptureMiddleware
from hexastack_events.ports.buses import DistributedEventBusPort
from hexastack_events.ports.outbox import (
    OutboxRelayPort,
    OutboxStoragePort,
)
from rodi import Container


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
