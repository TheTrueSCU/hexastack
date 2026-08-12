from typing import Any

from hexastack_core.utils.context import get_correlation_id
from strawberry.extensions import SchemaExtension


class CorrelationExtension(SchemaExtension):
    """Strawberry Schema Extension injecting correlation ID into GraphQL execution result.

    Notes/Architectural Intent:
        Aligns GraphQL execution with REST and CQRS telemetry by attaching
        the active async context's correlation_id into the GraphQL 'extensions' payload.
    """

    def get_results(self) -> dict[str, Any]:
        """Return extension dictionary to be merged into GraphQL ExecutionResult."""
        cid = get_correlation_id()
        if cid:
            return {"correlation_id": cid}
        return {}


__all__ = [
    "CorrelationExtension",
]
