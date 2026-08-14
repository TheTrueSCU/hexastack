from hexastack_auth.adapters.in_memory import (
    InMemoryPasswordHasher,
    InMemorySecurityService,
)
from hexastack_auth.adapters.jwt import JwtSecurityAdapter
from hexastack_auth.adapters.password import Pbkdf2PasswordHasher
from hexastack_auth.infra.config import HexastackAuthConfig, register_auth_config
from hexastack_auth.infra.middleware import AuthorizationMiddleware
from hexastack_auth.ports.password import PasswordHasherPort
from hexastack_auth.ports.security import SecurityPort
from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort


class AuthBootstrapper(BootstrapperPort):
    """Bootstrapper configuring authentication, token services, and CQRS security middleware.

    Notes/Architectural Intent:
        Executes at priority order=16 (before CQRS pipeline execution and HTTP driving layers).
        Registers PasswordHasherPort, SecurityPort, and AuthorizationMiddleware into the rodi Container.
    """

    order: int = 16
    name: str = "auth"

    def register_config(self, registry: ConfigRegistry) -> None:
        """Register the Auth configuration section in Phase 1.

        Args:
            registry: The active ConfigRegistry instance.
        """
        register_auth_config(registry)

    def configure(self, context: BootstrapContext) -> None:
        """Configure security ports, token adapters, and middleware in Phase 2.

        Args:
            context: The active BootstrapContext containing the DI Container.
        """
        di = context.container

        # 1. Read Auth Configuration
        if HexastackAuthConfig in di:
            cfg = di.resolve(HexastackAuthConfig)
        else:
            cfg = context.get_config("auth", HexastackAuthConfig)

        # 2. Instantiate Password Hasher
        hasher: PasswordHasherPort
        if cfg.hasher == "pbkdf2":
            hasher = Pbkdf2PasswordHasher()
        else:
            hasher = InMemoryPasswordHasher()

        # 3. Instantiate Security Port (Token Service)
        security_svc: SecurityPort
        if cfg.provider == "jwt":
            security_svc = JwtSecurityAdapter(
                secret_key=cfg.secret_key,
                algorithm=cfg.algorithm,
                default_ttl_seconds=cfg.token_expire_minutes * 60,
                issuer=cfg.issuer,
                audience=cfg.audience,
            )
        else:
            security_svc = InMemorySecurityService(
                default_ttl_seconds=cfg.token_expire_minutes * 60,
            )

        # 4. Register Ports in DI Container
        di.add_instance(hasher, declared_class=PasswordHasherPort)
        di.add_instance(security_svc, declared_class=SecurityPort)

        # 5. Instantiate & Register Authorization Middleware
        auth_middleware = AuthorizationMiddleware(enabled=cfg.enabled)
        di.add_instance(auth_middleware, declared_class=AuthorizationMiddleware)

        # 6. Store in context properties
        context.properties["auth_config"] = cfg
        context.properties["security_service"] = security_svc
        context.properties["password_hasher"] = hasher


__all__ = [
    "AuthBootstrapper",
]
