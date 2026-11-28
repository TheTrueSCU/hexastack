from typing import Literal

from pydantic import BaseModel, Field


class OidcConfig(BaseModel):
    """Configuration options for OIDC discovery and JWKS asymmetric JWT verification.

    Notes/Architectural Intent:
        Configures remote JWKS verification for federated identity providers such
        as Keycloak, Authentik, Authelia, Okta, and Entra ID while enforcing
        asymmetric algorithms and access-token vs. ID-token confusion protections.
    """

    enabled: bool = False
    issuer: str = ""
    audience: str = ""
    jwks_uri: str | None = None
    discovery_url: str | None = None
    algorithms: list[str] = Field(default_factory=lambda: ["RS256", "ES256", "EdDSA"])
    require_access_token_typ: bool = False
    reject_id_tokens: bool = True
    jwks_cache_ttl_seconds: int = 300
    roles_claim: str = "roles"
    permissions_claim: str = "permissions"
    tenant_claim: str = "tenant_id"
    leeway_seconds: int = 30


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


class HexastackAuthConfig(BaseModel):
    """Pydantic configuration model for Hexastack security and authentication subsystem.

    Notes/Architectural Intent:
        Parsed deterministically during Phase 1 configuration loading from pyproject.toml
        or hexastack.toml under the  section.
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
    provider: Literal["jwt", "memory", "oidc"] = Field(
        default="jwt",
        description="Security provider backend ('jwt', 'memory', or 'oidc').",
    )
    hasher: Literal["pbkdf2", "memory"] = Field(
        default="pbkdf2",
        description="Password hashing backend ('pbkdf2' or 'memory').",
    )
    oidc: OidcConfig = Field(default_factory=OidcConfig)
    opa: OpaConfig = Field(default_factory=OpaConfig)
    openfga: OpenFgaConfig = Field(default_factory=OpenFgaConfig)
    spiffe: SpiffeConfig = Field(default_factory=SpiffeConfig)
    enabled: bool = Field(
        default=True,
        description="Master flag to enable authentication middleware enforcement.",
    )


__all__ = [
    "HexastackAuthConfig",
    "OidcConfig",
    "OpaConfig",
    "OpenFgaConfig",
    "SpiffeConfig",
]
