"""Unit tests for QualBootstrapper.

Notes/Architectural Intent:
    Verifies that QualBootstrapper wires ports, adapters, and CQRS handlers
    into the dependency injection container and sets bootstrap properties.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from hexastack_qual.adapters.cqrs.handlers import (
    FormatStatementsHandler,
    GetPrHealthHandler,
    GetQualityScorecardHandler,
    GetTestImpactHandler,
    InspectMutantsHandler,
    RunMutationTestingHandler,
    RunSanityCheckHandler,
    SyncAgentAssetsHandler,
)
from hexastack_qual.adapters.hexaqual.runner import HexaqualRunnerAdapter
from hexastack_qual.infra.bootstrap import QualBootstrapper
from hexastack_qual.ports.auditor import QualityAuditorPort
from hexastack_qual.ports.diagnostics import PrDiagnosticPort
from hexastack_qual.ports.mutator import MutationInspectorPort
from rodi import Container

from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_cqrs.ports.buses import EventBusPort


def test_bootstrapper_metadata():
    """Verify bootstrapper name and execution order."""
    bootstrapper = QualBootstrapper()
    name = bootstrapper.name
    order = bootstrapper.order
    assert name == "qual"
    assert order == 36


def test_bootstrapper_configure_without_event_bus():
    """Verify container registration when no EventBusPort is present."""
    container = Container()
    config_reg = ConfigRegistry()
    context = BootstrapContext(
        container=container,
        config=MagicMock(),
        config_registry=config_reg,
    )

    bootstrapper = QualBootstrapper()
    bootstrapper.register_config(config_reg)
    bootstrapper.configure(context)

    # Ports registered
    auditor = container.resolve(QualityAuditorPort)
    assert isinstance(auditor, HexaqualRunnerAdapter)

    mutator = container.resolve(MutationInspectorPort)
    assert isinstance(mutator, HexaqualRunnerAdapter)

    diagnostics = container.resolve(PrDiagnosticPort)
    assert isinstance(diagnostics, HexaqualRunnerAdapter)

    # Handlers registered
    assert container.resolve(RunSanityCheckHandler) is not None
    assert container.resolve(FormatStatementsHandler) is not None
    assert container.resolve(RunMutationTestingHandler) is not None
    assert container.resolve(SyncAgentAssetsHandler) is not None
    assert container.resolve(GetQualityScorecardHandler) is not None
    assert container.resolve(InspectMutantsHandler) is not None
    assert container.resolve(GetTestImpactHandler) is not None
    assert container.resolve(GetPrHealthHandler) is not None

    # Context properties
    runner_prop = context.properties.get("qual_runner")
    assert isinstance(runner_prop, HexaqualRunnerAdapter)


def test_bootstrapper_configure_with_event_bus():
    """Verify container registration wires EventBusPort when present in DI."""
    container = Container()
    mock_bus = MagicMock(spec=EventBusPort)
    container.add_instance(mock_bus, declared_class=EventBusPort)

    config_reg = ConfigRegistry()
    context = BootstrapContext(
        container=container,
        config=MagicMock(),
        config_registry=config_reg,
    )

    bootstrapper = QualBootstrapper()
    bootstrapper.configure(context)

    sanity_handler = container.resolve(RunSanityCheckHandler)
    assert sanity_handler is not None
    assert sanity_handler._event_bus is mock_bus
