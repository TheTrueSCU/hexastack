from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.logging import LoggingPort
from hexastack_logging.infra.bootstrap import LoggingBootstrapper


def test_logging_bootstrapper():
    bootstrapper = LoggingBootstrapper()
    res = bootstrap(bootstrappers=[bootstrapper], auto_discover=False)

    assert LoggingPort in res.container
    logger = res.container.resolve(LoggingPort)
    assert logger is not None
    assert res.get("logger") is logger
