from typing import Literal

from pydantic import BaseModel, Field

from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry


class OpaConfig(BaseModel):
    """Configuration options for Open Policy Agent integration."""

    enabled: bool = False
    url: str = "http://localhost:8181"
    policy_path: str = "v1/data/authz/allow"
    timeout: float = 3.0


class OpenFgaConfig(BaseModel):
    """Configuration options for OpenFGA ReBAC integration."""

    enabled: bool = False
    api_url: str = "http://localhost:8080"
    store_id: str = ""
    model_id: str | None = None


class SpiffeConfig(BaseModel):
    """Configuration options for SPIFFE / SPIRE Workload Identity integration."""

    enabled: bool = False
    socket_path: str = "unix:///tmp/spire-agent/public/api.sock"
    trust_domain: str = "example.org"


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
    opa: OpaConfig = Field(default_factory=OpaConfig)
    openfga: OpenFgaConfig = Field(default_factory=OpenFgaConfig)
    spiffe: SpiffeConfig = Field(default_factory=SpiffeConfig)
    enabled: bool = Field(
        default=True,
        description="Master flag to enable authentication middleware enforcement.",
    )


__all__ = [
    "HexastackAuthConfig",
    "OpaConfig",
    "OpenFgaConfig",
    "register_auth_config",
    "SpiffeConfig",
]


def register_auth_config(registry: ConfigRegistry) -> None:
    """Register the auth configuration section in the global ConfigRegistry.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("auth", HexastackAuthConfig)
