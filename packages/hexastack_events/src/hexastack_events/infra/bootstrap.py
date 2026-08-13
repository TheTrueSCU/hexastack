from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_cqrs.ports.buses import EventBusPort

from hexastack_events.adapters.buses.in_memory import (
    InMemoryDistributedEventBus,
)
from hexastack_events.adapters.outbox.asyncio import AsyncioOutboxRelay
from hexastack_events.adapters.outbox.huey import HueyOutboxRelay
from hexastack_events.adapters.outbox.in_memory import InMemoryOutboxStorage
from hexastack_events.infra.config import (
    HexastackEventsConfig,
    register_events_config,
)
from hexastack_events.infra.middleware import OutboxCaptureMiddleware
from hexastack_events.ports.buses import DistributedEventBusPort
from hexastack_events.ports.outbox import (
    OutboxRelayPort,
    OutboxStoragePort,
)


class EventsBootstrapper(BootstrapperPort):
    """Bootstrapper assembling event streaming, outbox storage, and relay workers.

    Notes/Architectural Intent:
        Executes at priority order=22 (after CQRS pipeline registration at order=20).
        Binds OutboxStoragePort, DistributedEventBusPort, and OutboxRelayPort into DI.
    """

    order: int = 22
    name: str = "events"

    def register_config(self, registry: ConfigRegistry) -> None:
        """Register the events configuration section in Phase 1."""
        register_events_config(registry)

    def configure(self, context: BootstrapContext) -> None:
        """Configure event streaming and outbox components in Phase 2."""
        di = context.container

        # 1. Read Events Configuration
        if HexastackEventsConfig in di:
            cfg = di.resolve(HexastackEventsConfig)
        else:
            cfg = context.get_config("events", HexastackEventsConfig)

        # 2. Resolve or Bind OutboxStoragePort
        if OutboxStoragePort in di:
            storage = di.resolve(OutboxStoragePort)
        else:
            storage = InMemoryOutboxStorage()
            di.add_instance(storage, declared_class=OutboxStoragePort)

        # 3. Resolve or Bind DistributedEventBusPort
        if DistributedEventBusPort in di:
            bus = di.resolve(DistributedEventBusPort)
        elif EventBusPort in di:
            bus = di.resolve(EventBusPort)
        else:
            bus = InMemoryDistributedEventBus()
            di.add_instance(bus, declared_class=DistributedEventBusPort)
            di.add_instance(bus, declared_class=EventBusPort)

        # 4. Assemble Outbox Relay Worker
        relay: OutboxRelayPort | None = None
        if cfg.relay_mode == "asyncio":
            relay = AsyncioOutboxRelay(
                storage=storage,
                bus=bus,
                poll_interval_seconds=cfg.poll_interval_seconds,
                batch_size=cfg.batch_size,
            )
        elif cfg.relay_mode == "huey":
            relay = HueyOutboxRelay(
                storage=storage,
                bus=bus,
                batch_size=cfg.batch_size,
            )

        if relay is not None:
            di.add_instance(relay, declared_class=OutboxRelayPort)

        # 5. Assemble and Bind OutboxCaptureMiddleware
        capture_mw = OutboxCaptureMiddleware(
            storage=storage,
            source=cfg.source,
            enabled=cfg.enabled,
        )
        di.add_instance(capture_mw, declared_class=OutboxCaptureMiddleware)

        # 6. Store in context properties
        context.properties["events_config"] = cfg
        context.properties["outbox_storage"] = storage
        context.properties["distributed_bus"] = bus
        if relay is not None:
            context.properties["outbox_relay"] = relay


__all__ = [
    "EventsBootstrapper",
]
