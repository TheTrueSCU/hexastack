from hexastack_core.domain.generic import Generic


class Query[T](Generic):
    """Base class for all read-only Query objects in CQRS.

    Notes/Architectural Intent:
        Queries represent side-effect-free data retrieval requests expecting a return value of type T.
    """
