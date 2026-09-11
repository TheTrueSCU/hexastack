"""Atheris and coverage-guided security fuzzing suite for Hexastack.

Notes/Architectural Intent:
    Exports fuzz harnesses for LogSanitizer and ProtoCompiler ensuring
    monorepo-wide algorithmic ReDoS immunity and parser crash resilience.
"""

from fuzz.fuzz_log_sanitizer import (
    run_atheris as fuzz_log_sanitizer_atheris,
)
from fuzz.fuzz_log_sanitizer import (
    run_standalone as fuzz_log_sanitizer_standalone,
)
from fuzz.fuzz_proto_compiler import (
    run_atheris as fuzz_proto_compiler_atheris,
)
from fuzz.fuzz_proto_compiler import (
    run_standalone as fuzz_proto_compiler_standalone,
)

__all__ = [
    "fuzz_log_sanitizer_atheris",
    "fuzz_log_sanitizer_standalone",
    "fuzz_proto_compiler_atheris",
    "fuzz_proto_compiler_standalone",
]
