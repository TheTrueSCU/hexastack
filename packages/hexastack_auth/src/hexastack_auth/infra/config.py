from typing import Literal

from pydantic import BaseModel, Field

from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry


@config_section("auth")
class HexastackAuthConfig(BaseModel):
    """Pydantic configuration model for Hexastack security and authentication subsystem.

    Notes/Architectural Intent:
        Parsed deterministically during Phase 1 configuration loading from pyproject.toml
        or hexastack.toml under the `[hexastack.auth]` section.
    """

    secret_key: str = Field(
        default="hexastack-dev-secret-key-change-in-production",
        description="Cryptographic signing key for JWT tokens.",
    )
    algorithm: str = Field(
        default="HS256",
        description="Cryptographic algorithm for signing JWT tokens.",
    )
    token_expire_minutes: int = Field(
        default=60,
        description="Lifespan duration of issued JWT tokens in minutes.",
    )
    issuer: str | None = Field(
        default=None,
        description="Expected token issuer string ('iss' claim).",
    )
    audience: str | None = Field(
        default=None,
        description="Expected token audience string ('aud' claim).",
    )
    provider: Literal["jwt", "memory"] = Field(
        default="jwt",
        description="Security provider backend ('jwt' or 'memory').",
    )
    hasher: Literal["pbkdf2", "memory"] = Field(
        default="pbkdf2",
        description="Password hashing backend ('pbkdf2' or 'memory').",
    )
    enabled: bool = Field(
        default=True,
        description="Master flag to enable authentication middleware enforcement.",
    )


def register_auth_config(registry: ConfigRegistry) -> None:
    """Register the auth configuration section in the global ConfigRegistry.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("auth", HexastackAuthConfig)


__all__ = [
    "HexastackAuthConfig",
    "register_auth_config",
]
