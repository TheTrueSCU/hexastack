from collections.abc import Callable
from typing import Protocol

from hexastack_core.domain import Generic


class GenericMiddleware(Protocol):
    """Protocol defining the interface for CQRS middleware components.

    Notes/Architectural Intent:
        Middleware wraps handler invocation to intercept processing, apply cross-cutting
        concerns (e.g. retry, logging, validation), and pass control down the execution chain.
    """

    def __call__[G: Generic, R](
        self,
        instance: G,
        next_call: Callable[[G], R],
    ) -> R:
        """Invoke middleware logic and pass execution to next_call.

        Args:
            instance: The command or query message instance.
            next_call: Callable representing the remaining middleware/handler chain.

        Returns:
            The result returned from downstream processing.

        Raises:
            Exception: Re-raises unhandled exceptions or domain errors.
        """
        ...
