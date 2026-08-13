from hexastack_auth.adapters.in_memory import InMemorySecurityService
from hexastack_auth.adapters.jwt import JwtSecurityAdapter
from hexastack_auth.adapters.password import Pbkdf2PasswordHasher
from hexastack_auth.infra.bootstrap import AuthBootstrapper
from hexastack_auth.infra.config import HexastackAuthConfig
from hexastack_auth.infra.middleware import AuthorizationMiddleware
from hexastack_auth.ports.password import PasswordHasherPort
from hexastack_auth.ports.security import SecurityPort
from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from rodi import Container


def test_auth_bootstrapper_configuration_jwt():
    bootstrapper = AuthBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    sec_svc = container.resolve(SecurityPort)
    assert isinstance(sec_svc, JwtSecurityAdapter)

    hasher = container.resolve(PasswordHasherPort)
    assert isinstance(hasher, Pbkdf2PasswordHasher)

    middleware = container.resolve(AuthorizationMiddleware)
    assert isinstance(middleware, AuthorizationMiddleware)


def test_auth_bootstrapper_configuration_in_memory():
    bootstrapper = AuthBootstrapper()
    container = Container()
    config_reg = ConfigRegistry()
    bootstrapper.register_config(config_reg)

    # Supply in-memory auth config in DI container
    mem_config = HexastackAuthConfig(provider="memory", hasher="memory")
    container.add_instance(mem_config, declared_class=HexastackAuthConfig)

    ctx = BootstrapContext(container=container, config=None, config_registry=config_reg)
    bootstrapper.configure(ctx)

    sec_svc = container.resolve(SecurityPort)
    assert isinstance(sec_svc, InMemorySecurityService)
