"""Backward compatibility shim for LogSanitizer relocated to hexastack_logging.utils.sanitizer.

Notes/Architectural Intent:
    LogSanitizer is a pure data scrubber with no infrastructure dependencies, relocated to
    hexastack_logging.utils.sanitizer. This module re-exports it to preserve backward compatibility.
"""

from hexastack_logging.utils.sanitizer import (
    _DEFAULT_MASKED_KEYS,
    _DEFAULT_PATTERNS,
    LogSanitizer,
)

__all__ = [
    "_DEFAULT_MASKED_KEYS",
    "_DEFAULT_PATTERNS",
    "LogSanitizer",
]
