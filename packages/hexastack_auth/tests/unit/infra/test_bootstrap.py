from rodi import Container

from hexastack_auth.adapters.in_memory import (
    InMemoryPasswordHasher,
    InMemorySecurityService,
)
from hexastack_auth.adapters.jwt import JwtSecurityAdapter
from hexastack_auth.adapters.password import Pbkdf2PasswordHasher
from hexastack_auth.infra.bootstrap import AuthBootstrapper
from hexastack_auth.infra.config import HexastackAuthConfig
from hexastack_auth.infra.middleware import AuthorizationMiddleware
from hexastack_auth.ports.password import PasswordHasherPort
from hexastack_auth.ports.security import SecurityPort
from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry


def test_auth_bootstrapper_configuration_in_memory():
    bootstrapper = AuthBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    # Supply in-memory auth config in DI container
    mem_config = HexastackAuthConfig(
        provider="memory",
        hasher="memory",
        token_expire_minutes=30,
        enabled=False,
    )
    container.add_instance(mem_config, declared_class=HexastackAuthConfig)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    sec_svc = container.resolve(SecurityPort)
    assert isinstance(sec_svc, InMemorySecurityService)
    assert sec_svc._default_ttl_seconds == 1800

    hasher = container.resolve(PasswordHasherPort)
    assert isinstance(hasher, InMemoryPasswordHasher)

    middleware = container.resolve(AuthorizationMiddleware)
    assert isinstance(middleware, AuthorizationMiddleware)
    assert middleware.enabled is False

    assert ctx.properties["auth_config"] is mem_config
    assert ctx.properties["security_service"] is sec_svc
    assert ctx.properties["password_hasher"] is hasher


def test_auth_bootstrapper_configuration_jwt():
    bootstrapper = AuthBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    sec_svc = container.resolve(SecurityPort)
    assert isinstance(sec_svc, JwtSecurityAdapter)
    assert sec_svc._algorithm == "HS256"
    assert sec_svc._default_ttl.total_seconds() == 3600

    hasher = container.resolve(PasswordHasherPort)
    assert isinstance(hasher, Pbkdf2PasswordHasher)

    middleware = container.resolve(AuthorizationMiddleware)
    assert isinstance(middleware, AuthorizationMiddleware)
    assert middleware.enabled is True

    assert ctx.properties["auth_config"].secret_key == (
        "hexastack-dev-secret-key-change-in-production"
    )
    assert ctx.properties["security_service"] is sec_svc
    assert ctx.properties["password_hasher"] is hasher


def test_auth_bootstrapper_properties():
    bootstrapper = AuthBootstrapper()
    assert bootstrapper.order == 16
    assert bootstrapper.name == "auth"


def test_auth_bootstrapper_opa_openfga_and_spiffe_configurations():
    """Verify AuthBootstrapper configuring OPA, OpenFGA, and SPIFFE adapters."""
    from hexastack_auth.adapters.opa.policy import OpaPolicyAdapter
    from hexastack_auth.adapters.openfga.policy import OpenFgaPolicyAdapter
    from hexastack_auth.adapters.spiffe.workload import SpiffeWorkloadAdapter
    from hexastack_auth.infra.config import (
        OpaConfig,
        OpenFgaConfig,
        SpiffeConfig,
    )
    from hexastack_auth.ports.policy import AuthorizationPolicyPort
    from hexastack_auth.ports.workload import WorkloadIdentityPort

    bootstrapper = AuthBootstrapper()

    # 1. OPA + SPIFFE
    c1 = Container()
    cfg1 = HexastackAuthConfig(
        opa=OpaConfig(enabled=True, url="http://localhost:8181"),
        spiffe=SpiffeConfig(
            enabled=True,
            socket_path="unix:///tmp/spire.sock",
            trust_domain="example.org",
        ),
    )
    c1.add_instance(cfg1, declared_class=HexastackAuthConfig)
    ctx1 = BootstrapContext(container=c1, config=None, config_registry=ConfigRegistry())
    bootstrapper.configure(ctx1)

    assert isinstance(c1.resolve(AuthorizationPolicyPort), OpaPolicyAdapter)
    assert isinstance(c1.resolve(WorkloadIdentityPort), SpiffeWorkloadAdapter)

    # 2. OpenFGA
    c2 = Container()
    cfg2 = HexastackAuthConfig(
        openfga=OpenFgaConfig(
            enabled=True,
            api_url="http://localhost:8080",
            store_id="store1",
            model_id="model1",
        ),
    )
    c2.add_instance(cfg2, declared_class=HexastackAuthConfig)
    ctx2 = BootstrapContext(container=c2, config=None, config_registry=ConfigRegistry())
    bootstrapper.configure(ctx2)

    assert isinstance(c2.resolve(AuthorizationPolicyPort), OpenFgaPolicyAdapter)
