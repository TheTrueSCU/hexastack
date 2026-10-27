"""Identity and identifier obfuscation adapters.

Notes/Architectural Intent:
    Exports HashidsAdapter and InMemoryIdObfuscator for reversible ID tokenization.
"""

from hexastack_core.adapters.identity.hashids import HashidsAdapter
from hexastack_core.adapters.identity.in_memory import InMemoryIdObfuscator

__all__ = [
    "HashidsAdapter",
    "InMemoryIdObfuscator",
]
