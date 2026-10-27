"""Unit test validating IdObfuscatorPort contract.

Notes/Architectural Intent:
    Verifies that IdObfuscatorPort interface definitions enforce
    required encode and decode signatures across implementations.
"""

import inspect

from hexastack_core.ports.identity import IdObfuscatorPort


def test_id_obfuscator_port_is_abstract() -> None:
    """Verify that IdObfuscatorPort cannot be instantiated directly."""
    is_abs = inspect.isabstract(IdObfuscatorPort)
    assert is_abs is True


def test_id_obfuscator_port_methods_exist() -> None:
    """Verify abstract methods on IdObfuscatorPort."""
    methods = {"encode", "decode", "encode_many", "decode_many"}
    abstracts = IdObfuscatorPort.__abstractmethods__
    diff = methods.difference(abstracts)
    assert len(diff) == 0
