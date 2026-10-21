"""Backward compatibility shim for mixins relocated to hexastack_db.utils.mixins.

Notes/Architectural Intent:
    HexastackBase, UuidPrimaryKeyMixin, and TimestampMixin are reusable ORM mixins
    with no infrastructure dependencies, relocated to hexastack_db.utils.mixins.
    This module re-exports them to preserve backward compatibility.
"""

from hexastack_db.utils.mixins import (
    HexastackBase,
    TimestampMixin,
    UuidPrimaryKeyMixin,
)

__all__ = [
    "HexastackBase",
    "TimestampMixin",
    "UuidPrimaryKeyMixin",
]
