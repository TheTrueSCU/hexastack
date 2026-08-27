"""CNCF OpenFeature flag adapter implementation.

Notes/Architectural Intent:
    Adapts the OpenFeature Python SDK (openfeature.api) to Hexastack's FeatureFlagPort.
    Translates ambient UserContext / EvaluationContext seamlessly to OpenFeature
    EvaluationContext and evaluates boolean, string, int, float, and JSON flags.
"""

from collections.abc import Mapping
from typing import Any

import openfeature.api
from openfeature.client import OpenFeatureClient
from openfeature.evaluation_context import EvaluationContext as OfEvaluationContext

from hexastack_core.domain.feature_flags import (
    EvaluationContext,
    FlagEvaluationDetails,
    FlagEvaluationReason,
)
from hexastack_core.ports.feature_flags import FeatureFlagPort

__all__ = [
    "OpenFeatureFlagAdapter",
]


class OpenFeatureFlagAdapter(FeatureFlagPort):
    """FeatureFlagPort implementation delegating evaluations to OpenFeature SDK.

    Notes/Architectural Intent:
        Wraps an OpenFeature Client instance, connecting Hexastack application
        layers (CQRS, FastAPI, CLI, GraphQL) to any configured OpenFeature provider.
    """

    def __init__(
        self,
        client: OpenFeatureClient | None = None,
        client_name: str | None = None,
    ) -> None:
        self._client = client or openfeature.api.get_client(client_name)

    def get_all_flags(self) -> dict[str, Any]:
        """Introspect active flags from the underlying OpenFeature provider if supported.

        Returns:
            Dictionary mapping flag keys to their configured status/values.
        """
        flags: dict[str, Any] = {}
        try:
            provider: Any = openfeature.api.provider_registry.get_default_provider()
            provider_flags = getattr(provider, "_flags", None)
            if isinstance(provider_flags, dict):
                for k, v in provider_flags.items():
                    # If InMemoryFlag object, resolve current variant/value
                    if hasattr(v, "variants") and hasattr(v, "default_variant"):
                        flags[str(k)] = v.variants.get(
                            v.default_variant, v.default_variant
                        )
                    elif hasattr(v, "state"):
                        flags[str(k)] = str(v.state)
                    else:
                        flags[str(k)] = v
        except Exception:
            pass
        return flags

    def get_boolean_details(
        self,
        flag_key: str,
        default: bool = False,
        context: EvaluationContext | None = None,
    ) -> FlagEvaluationDetails[bool]:
        """Evaluate a boolean flag returning comprehensive evaluation metadata."""
        of_ctx = _to_openfeature_context(
            context or EvaluationContext.from_current_context()
        )
        details = self._client.get_boolean_details(
            flag_key=flag_key,
            default_value=default,
            evaluation_context=of_ctx,
        )
        reason: FlagEvaluationReason = FlagEvaluationReason.UNKNOWN
        if details.reason:
            try:
                reason = FlagEvaluationReason(str(details.reason).upper())
            except ValueError:
                reason = FlagEvaluationReason.UNKNOWN

        return FlagEvaluationDetails(
            flag_key=details.flag_key,
            value=details.value,
            reason=reason,
            variant=details.variant,
            error_code=str(details.error_code) if details.error_code else None,
        )

    def get_boolean_value(
        self,
        flag_key: str,
        default: bool = False,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Evaluate a boolean feature flag."""
        of_ctx = _to_openfeature_context(
            context or EvaluationContext.from_current_context()
        )
        return self._client.get_boolean_value(
            flag_key=flag_key,
            default_value=default,
            evaluation_context=of_ctx,
        )

    def get_float_value(
        self,
        flag_key: str,
        default: float = 0.0,
        context: EvaluationContext | None = None,
    ) -> float:
        """Evaluate a floating-point feature flag."""
        of_ctx = _to_openfeature_context(
            context or EvaluationContext.from_current_context()
        )
        return self._client.get_float_value(
            flag_key=flag_key,
            default_value=default,
            evaluation_context=of_ctx,
        )

    def get_integer_value(
        self,
        flag_key: str,
        default: int = 0,
        context: EvaluationContext | None = None,
    ) -> int:
        """Evaluate an integer feature flag."""
        of_ctx = _to_openfeature_context(
            context or EvaluationContext.from_current_context()
        )
        return self._client.get_integer_value(
            flag_key=flag_key,
            default_value=default,
            evaluation_context=of_ctx,
        )

    def get_object_value(
        self,
        flag_key: str,
        default: Mapping[str, Any] | None = None,
        context: EvaluationContext | None = None,
    ) -> Mapping[str, Any]:
        """Evaluate a structured JSON object feature flag."""
        of_ctx = _to_openfeature_context(
            context or EvaluationContext.from_current_context()
        )
        default_val = dict(default) if default is not None else {}
        res = self._client.get_object_value(
            flag_key=flag_key,
            default_value=default_val,
            evaluation_context=of_ctx,
        )
        return res if isinstance(res, Mapping) else default_val

    def get_string_value(
        self,
        flag_key: str,
        default: str = "",
        context: EvaluationContext | None = None,
    ) -> str:
        """Evaluate a string/variant feature flag."""
        of_ctx = _to_openfeature_context(
            context or EvaluationContext.from_current_context()
        )
        return self._client.get_string_value(
            flag_key=flag_key,
            default_value=default,
            evaluation_context=of_ctx,
        )

    def is_enabled(
        self,
        flag_key: str,
        default: bool = False,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Evaluate whether a boolean feature flag is enabled."""
        return self.get_boolean_value(
            flag_key=flag_key, default=default, context=context
        )


def _to_openfeature_context(
    context: EvaluationContext | None,
) -> OfEvaluationContext | None:
    """Convert Hexastack EvaluationContext to OpenFeature EvaluationContext."""
    if context is None:
        return None

    targeting_key = context.targeting_key or context.user_id or ""
    attributes: dict[str, Any] = dict(context.attributes)
    if context.user_id:
        attributes["user_id"] = context.user_id
    if context.tenant_id:
        attributes["tenant_id"] = context.tenant_id
    if context.roles:
        attributes["roles"] = list(context.roles)

    return OfEvaluationContext(
        targeting_key=targeting_key,
        attributes=attributes,
    )
