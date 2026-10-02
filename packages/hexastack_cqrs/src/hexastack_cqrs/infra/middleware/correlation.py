from typing import Any

from hexastack_core.domain import Generic
from hexastack_core.utils.context import (
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)
from hexastack_cqrs.infra.middleware.generic import InOutMiddleware


class CorrelationMiddleware(InOutMiddleware):
    """Middleware establishing and propagating correlation IDs across message execution.

    Notes/Architectural Intent:
        Inherits from InOutMiddleware to extract correlation_id from incoming message
        attributes if present, or initialize a new correlation ID in the execution context,
        ensuring continuous tracing across handlers.
    """

    def __init__(self, generate_if_missing: bool = True) -> None:
        """Initialize CorrelationMiddleware.

        Args:
            generate_if_missing: If True, automatically generates a new UUID when no correlation ID exists.
        """
        self._generate_if_missing = generate_if_missing

    def before(self, instance: Generic) -> Any:
        """Establish or propagate correlation ID before downstream handler execution.

        Args:
            instance: Dispatched command, query, or event message instance.

        Returns:
            None.
        """
        existing_msg_cid = getattr(instance, "correlation_id", None)

        if existing_msg_cid:
            set_correlation_id(str(existing_msg_cid))
        elif not get_correlation_id() and self._generate_if_missing:
            new_correlation_id()
        return None


__all__ = [
    "CorrelationMiddleware",
]
