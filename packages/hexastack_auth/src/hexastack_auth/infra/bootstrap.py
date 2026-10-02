from hexastack_auth.adapters.in_memory import (
    InMemoryPasswordHasher,
    InMemorySecurityService,
)
from hexastack_auth.adapters.jwt import JwtSecurityAdapter
from hexastack_auth.adapters.password import Pbkdf2PasswordHasher
from hexastack_auth.infra.config import HexastackAuthConfig, register_auth_config
from hexastack_auth.infra.middleware import AuthorizationMiddleware
from hexastack_auth.ports.password import PasswordHasherPort
from hexastack_auth.ports.policy import AuthorizationPolicyPort
from hexastack_auth.ports.security import SecurityPort
from hexastack_auth.ports.workload import WorkloadIdentityPort
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

        # 4. Instantiate Policy and Workload Adapters if configured
        policy_adapter: AuthorizationPolicyPort | None = None
        if cfg.opa.enabled:
            from hexastack_auth.adapters.opa.policy import OpaPolicyAdapter

            policy_adapter = OpaPolicyAdapter(
                base_url=cfg.opa.url,
                default_policy_path=cfg.opa.policy_path,
                timeout=cfg.opa.timeout,
            )
            di.add_instance(policy_adapter, declared_class=AuthorizationPolicyPort)
        elif cfg.openfga.enabled:
            from hexastack_auth.adapters.openfga.policy import OpenFgaPolicyAdapter

            policy_adapter = OpenFgaPolicyAdapter(
                api_url=cfg.openfga.api_url,
                store_id=cfg.openfga.store_id,
                model_id=cfg.openfga.model_id,
            )
            di.add_instance(policy_adapter, declared_class=AuthorizationPolicyPort)

        if cfg.spiffe.enabled:
            from hexastack_auth.adapters.spiffe.workload import SpiffeWorkloadAdapter

            workload_adapter = SpiffeWorkloadAdapter(
                socket_path=cfg.spiffe.socket_path,
                trust_domain=cfg.spiffe.trust_domain,
            )
            di.add_instance(workload_adapter, declared_class=WorkloadIdentityPort)

        # 5. Register Ports in DI Container
        di.add_instance(hasher, declared_class=PasswordHasherPort)
        di.add_instance(security_svc, declared_class=SecurityPort)

        # 6. Instantiate and Register CQRS Authorization Middleware
        auth_middleware = AuthorizationMiddleware(
            enabled=cfg.enabled,
            policy_adapter=policy_adapter,
        )
        di.add_instance(auth_middleware, declared_class=AuthorizationMiddleware)

        # 7. Store in context properties
        context.properties["auth_config"] = cfg
        context.properties["security_service"] = security_svc
        context.properties["password_hasher"] = hasher

    def register_config(self, registry: ConfigRegistry) -> None:
        """Register the Auth configuration section in Phase 1.

        Args:
            registry: The active ConfigRegistry instance.
        """
        register_auth_config(registry)


__all__ = [
    "AuthBootstrapper",
]
