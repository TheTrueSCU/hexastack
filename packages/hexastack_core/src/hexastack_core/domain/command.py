from hexastack_core.domain.generic import Generic


class Command(Generic):
    """Base class for all intent-capturing Command objects in CQRS.

    Notes/Architectural Intent:
        Commands represent state-changing requests intended to be processed by a single handler.
    """
