from sqlalchemy import MetaData

_registry: list[MetaData] = []


def register_metadata(metadata: MetaData) -> None:
    """Register a SQLAlchemy MetaData object for use with auto_create_tables.

    Notes/Architectural Intent:
        Allows user applications to register their declarative base metadata so
        the DatabaseBootstrapper can call create_all() during bootstrap when
        auto_create_tables=True, without the bootstrapper needing to know about
        specific model modules at design time.

    Args:
        metadata: SQLAlchemy MetaData instance (typically DeclarativeBase.metadata).

    Returns:
        None.

    Raises:
        None.
    """
    if metadata not in _registry:
        _registry.append(metadata)


def get_registered_metadata() -> list[MetaData]:
    """Return a snapshot of all registered MetaData objects.

    Returns:
        List of registered SQLAlchemy MetaData instances.
    """
    return list(_registry)


def clear_metadata_registry() -> None:
    """Clear all registered MetaData objects.

    Notes/Architectural Intent:
        Primarily used in tests to reset state between test cases.

    Returns:
        None.
    """
    _registry.clear()


__all__ = [
    "clear_metadata_registry",
    "get_registered_metadata",
    "register_metadata",
]
