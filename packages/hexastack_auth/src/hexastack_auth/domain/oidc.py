"""Pure domain primitives for OAuth2 PKCE (S256) and OpenID Connect verification.

Notes/Architectural Intent:
    Maintains zero external framework or HTTP client dependencies (ADR-001). Provides
    RFC 7636 PKCE S256 generation/verification, CSPRNG OIDC nonces, discovery
    metadata value objects, and strict asymmetric token validation policies.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS: tuple[str, ...] = (
    "RS256",
    "RS384",
    "RS512",
    "ES256",
    "ES384",
    "ES512",
    "PS256",
    "PS384",
    "PS512",
    "EdDSA",
)

FORBIDDEN_OIDC_ALGORITHMS: frozenset[str] = frozenset(
    {"none", "HS256", "HS384", "HS512"}
)

_PKCE_MIN_LENGTH = 43
_PKCE_MAX_LENGTH = 128
_PKCE_VERIFIER_RE = re.compile(r"^[A-Za-z0-9\-._~]+$")
_PKCE_UNRESERVED_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)


def _require_non_empty_str(data: Mapping[str, Any], key: str) -> str:
    """Extract and validate a required non-empty string metadata field."""
    val = data.get(key)
    if not isinstance(val, str) or not val.strip():
        msg = f"OIDC discovery document missing required non-empty '{key}' field."
        raise ValueError(msg)
    return val.strip()


def _optional_str(data: Mapping[str, Any], key: str) -> str | None:
    """Extract an optional non-empty string field from discovery metadata."""
    val = data.get(key)
    if val is None:
        return None
    if isinstance(val, str) and val.strip():
        return val.strip()
    return None


def _string_tuple(data: Mapping[str, Any], key: str) -> tuple[str, ...]:
    """Extract a tuple of strings from an optional discovery list field."""
    val = data.get(key)
    if val is None:
        return ()
    if isinstance(val, (list, tuple)):
        return tuple(
            str(item) for item in val if isinstance(item, str) and item.strip()
        )
    return ()


def _validate_audience(audience: str | tuple[str, ...]) -> None:
    """Validate that an OIDC policy audience is non-empty."""
    if isinstance(audience, str):
        if not audience.strip():
            msg = "OIDC policy 'audience' cannot be empty."
            raise ValueError(msg)
        return
    if not audience or any(not item.strip() for item in audience):
        msg = "OIDC policy 'audience' tuple must contain non-empty strings."
        raise ValueError(msg)


def _validate_asymmetric_algorithms(algorithms: tuple[str, ...]) -> None:
    """Validate that allowed algorithms are non-empty and exclude 'none'/HS*."""
    if not algorithms:
        msg = "OIDC policy 'allowed_algorithms' cannot be empty."
        raise ValueError(msg)
    for alg in algorithms:
        normalized = alg.strip()
        lowered = normalized.casefold()
        if not normalized:
            msg = "OIDC policy 'allowed_algorithms' entries cannot be blank."
            raise ValueError(msg)
        if (
            lowered == "none"
            or lowered.startswith("hs")
            or normalized in FORBIDDEN_OIDC_ALGORITHMS
        ):
            msg = (
                f"Algorithm '{alg}' is forbidden for OIDC JWKS verification; "
                "only asymmetric signature algorithms are allowed."
            )
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class PkceCodePair:
    """Immutable RFC 7636 PKCE verifier/challenge pair using ``S256``.

    Notes/Architectural Intent:
        Restricts ``code_challenge_method`` to ``S256`` so callers never emit
        downgraded ``plain`` challenges over authorization redirects.
    """

    code_verifier: str
    code_challenge: str
    code_challenge_method: Literal["S256"] = "S256"


@dataclass(frozen=True, slots=True)
class OAuthAuthorizationRequest:
    """Authorization redirect payload bundling anti-CSRF state, PKCE, and nonce.

    Notes/Architectural Intent:
        Captures the ephemeral client-side secrets generated alongside an OAuth2
        redirect URL so driving routers can bind and verify them on callback.
    """

    url: str
    state: str
    code_verifier: str | None = None
    code_challenge: str | None = None
    code_challenge_method: str | None = None
    nonce: str | None = None


@dataclass(frozen=True, slots=True)
class OidcDiscoveryDocument:
    """Normalized ``/.well-known/openid-configuration`` metadata document.

    Notes/Architectural Intent:
        Represents core OpenID Provider endpoints and supported capabilities as
        a pure value object decoupled from HTTP transport libraries.
    """

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str | None = None
    end_session_endpoint: str | None = None
    id_token_signing_alg_values_supported: tuple[str, ...] = ()
    code_challenge_methods_supported: tuple[str, ...] = ()
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> OidcDiscoveryDocument:
        """Construct an ``OidcDiscoveryDocument`` from parsed discovery JSON.

        Args:
            data: Mapping parsed from ``/.well-known/openid-configuration``.

        Returns:
            Validated immutable ``OidcDiscoveryDocument`` instance.

        Raises:
            ValueError: If any required discovery field is missing or blank.

        Notes/Architectural Intent:
            Fails fast on incomplete provider metadata before any network key
            resolution or token verification occurs.
        """
        return cls(
            issuer=_require_non_empty_str(data, "issuer"),
            authorization_endpoint=_require_non_empty_str(
                data, "authorization_endpoint"
            ),
            token_endpoint=_require_non_empty_str(data, "token_endpoint"),
            jwks_uri=_require_non_empty_str(data, "jwks_uri"),
            userinfo_endpoint=_optional_str(data, "userinfo_endpoint"),
            end_session_endpoint=_optional_str(data, "end_session_endpoint"),
            id_token_signing_alg_values_supported=_string_tuple(
                data, "id_token_signing_alg_values_supported"
            ),
            code_challenge_methods_supported=_string_tuple(
                data, "code_challenge_methods_supported"
            ),
            raw_metadata=dict(data),
        )


@dataclass(frozen=True, slots=True)
class OidcTokenPolicy:
    """Strict validation policy governing OIDC JWKS token verification.

    Notes/Architectural Intent:
        Enforces asymmetric signature algorithms, mandatory issuer/audience
        validation, and access-token vs. ID-token confusion defenses.
    """

    issuer: str
    audience: str | tuple[str, ...]
    allowed_algorithms: tuple[str, ...] = DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS
    require_access_token_typ: bool = False
    reject_id_tokens: bool = True
    roles_claim: str = "roles"
    permissions_claim: str = "permissions"
    tenant_claim: str = "tenant_id"
    leeway_seconds: int = 30

    def __post_init__(self) -> None:
        """Validate policy invariants at construction time."""
        if not self.issuer.strip():
            msg = "OIDC policy 'issuer' cannot be empty."
            raise ValueError(msg)
        _validate_audience(self.audience)
        _validate_asymmetric_algorithms(self.allowed_algorithms)
        if self.leeway_seconds < 0:
            msg = "OIDC policy 'leeway_seconds' cannot be negative."
            raise ValueError(msg)


def compute_pkce_s256_challenge(code_verifier: str) -> str:
    """Compute an RFC 7636 ``S256`` PKCE code challenge from a verifier string.

    Args:
        code_verifier: High-entropy RFC 7636 unreserved ASCII string (43–128 chars).

    Returns:
        Unpadded base64url-encoded SHA-256 digest of ``code_verifier``.

    Raises:
        ValueError: If ``code_verifier`` violates RFC 7636 length or charset rules.

    Notes/Architectural Intent:
        Enforces strict RFC 7636 Section 4.1 syntax validation so weak or
        malformed verifiers never reach upstream token endpoints.
    """
    if not (
        _PKCE_MIN_LENGTH <= len(code_verifier) <= _PKCE_MAX_LENGTH
        and _PKCE_VERIFIER_RE.fullmatch(code_verifier)
    ):
        msg = (
            "PKCE code_verifier must be 43..128 characters from RFC 7636 "
            "unreserved set [A-Za-z0-9-._~]."
        )
        raise ValueError(msg)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_pkce_pair(length: int = 64) -> PkceCodePair:
    """Generate a cryptographically random PKCE verifier and ``S256`` challenge.

    Args:
        length: Verifier length in characters (43–128, default 64).

    Returns:
        ``PkceCodePair`` containing the verifier, S256 challenge, and method.

    Raises:
        ValueError: If ``length`` falls outside ``[43, 128]``.

    Notes/Architectural Intent:
        Uses ``secrets.choice`` over RFC 7636 unreserved characters so generated
        verifiers maximize entropy within OAuth2 specification bounds.
    """
    if not (_PKCE_MIN_LENGTH <= length <= _PKCE_MAX_LENGTH):
        msg = f"PKCE verifier length must be between 43 and 128, got {length}."
        raise ValueError(msg)
    verifier = "".join(secrets.choice(_PKCE_UNRESERVED_CHARS) for _ in range(length))
    challenge = compute_pkce_s256_challenge(verifier)
    return PkceCodePair(
        code_verifier=verifier,
        code_challenge=challenge,
        code_challenge_method="S256",
    )


def verify_pkce_s256(code_verifier: str, code_challenge: str) -> bool:
    """Verify a PKCE ``code_verifier`` against an ``S256`` ``code_challenge``.

    Args:
        code_verifier: Candidate verifier submitted to the token endpoint.
        code_challenge: Stored ``S256`` challenge bound to the authorization code.

    Returns:
        ``True`` if ``code_verifier`` is valid RFC 7636 syntax and matches
        ``code_challenge`` in constant time; ``False`` otherwise.

    Raises:
        None.

    Notes/Architectural Intent:
        Uses ``hmac.compare_digest`` and returns ``False`` on malformed verifiers
        to avoid leaking character/length timing signals.
    """
    if not code_challenge:
        return False
    try:
        computed = compute_pkce_s256_challenge(code_verifier)
    except ValueError:
        return False
    return hmac.compare_digest(computed, code_challenge)


def generate_oidc_nonce(nbytes: int = 32) -> str:
    """Generate a CSPRNG URL-safe nonce for OpenID Connect ID token binding.

    Args:
        nbytes: Number of random entropy bytes (minimum 16, default 32).

    Returns:
        URL-safe random nonce string.

    Raises:
        ValueError: If ``nbytes`` is less than 16.

    Notes/Architectural Intent:
        Enforces at least 128 bits of entropy per OIDC Core Section 15.5.2.
    """
    if nbytes < 16:
        msg = f"OIDC nonce requires at least 16 bytes of entropy, got {nbytes}."
        raise ValueError(msg)
    return secrets.token_urlsafe(nbytes)


__all__ = [
    "compute_pkce_s256_challenge",
    "DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS",
    "FORBIDDEN_OIDC_ALGORITHMS",
    "generate_oidc_nonce",
    "generate_pkce_pair",
    "OAuthAuthorizationRequest",
    "OidcDiscoveryDocument",
    "OidcTokenPolicy",
    "PkceCodePair",
    "verify_pkce_s256",
]
