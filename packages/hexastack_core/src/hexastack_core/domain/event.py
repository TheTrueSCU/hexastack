from hexastack_core.domain.generic import Generic


class Event(Generic):
    """Base class for all domain Event notifications in CQRS.

    Notes/Architectural Intent:
        Events record facts about state changes that have occurred and can be broadcast to multiple listeners.
    """
