"""Domain exceptions for hexastack-qual.

Notes/Architectural Intent:
    Defines the domain-level exception hierarchy for architectural boundary,
    complexity, and parity violations. Decouples callers from external tool
    exceptions.
"""

from __future__ import annotations


class QualityError(Exception):
    """Base exception for all domain quality errors.

    Notes/Architectural Intent:
        All quality domain exceptions inherit from this root to allow callers
        to catch broad quality errors while discriminating on specific failure
        modes.
    """


class ComplexityExceededError(QualityError):
    """Raised when cognitive complexity exceeds configured thresholds.

    Args:
        function_name: Name of the offending function or method.
        file_path: Source file path where the violation occurred.
        complexity: Measured cognitive complexity score.
        threshold: Maximum allowable cognitive complexity.

    Notes/Architectural Intent:
        Encapsulates offending function coordinates to assist AI agents or
        developers in decomposing high-complexity functions.
    """

    def __init__(
        self,
        function_name: str,
        file_path: str,
        complexity: int,
        threshold: int = 25,
    ) -> None:
        self.function_name = function_name
        self.file_path = file_path
        self.complexity = complexity
        self.threshold = threshold
        msg = (
            f"Function '{function_name}' in {file_path} exceeded max complexity "
            f"threshold ({complexity} > {threshold})"
        )
        super().__init__(msg)


class ParityViolationError(QualityError):
    """Raised when 1:1 test symmetry between source and test files is broken.

    Args:
        missing_tests: List of missing unit test file paths.

    Notes/Architectural Intent:
        Enforces test parity invariants across all packages.
    """

    def __init__(self, missing_tests: list[str]) -> None:
        self.missing_tests = missing_tests
        count = len(missing_tests)
        msg = f"Test parity violation: {count} missing unit test file(s)"
        super().__init__(msg)


class StatementIntegrityError(QualityError):
    """Raised when __all__ export lists are unsorted or invalid.

    Args:
        invalid_files: List of file paths failing __all__ integrity checks.

    Notes/Architectural Intent:
        Fails fast when public export lists violate casefold ordering.
    """

    def __init__(self, invalid_files: list[str]) -> None:
        self.invalid_files = invalid_files
        count = len(invalid_files)
        msg = f"Statement integrity violation: {count} file(s) with unsorted __all__"
        super().__init__(msg)


class QualityGateFailedError(QualityError):
    """Raised when a quality sanity check fails.

    Args:
        check_name: Name of the failed sanity check.
        details: Specific error or diagnostic details.

    Notes/Architectural Intent:
        Signals an overall quality gate failure during CQRS execution.
    """

    def __init__(self, check_name: str, details: str) -> None:
        self.check_name = check_name
        self.details = details
        msg = f"Quality gate '{check_name}' failed: {details}"
        super().__init__(msg)


class AdapterNotAvailableError(QualityError):
    """Raised when an optional adapter extra is invoked without installed dependencies.

    Args:
        extra_name: The name of the missing extra (e.g. 'mcp', 'ui', 'events').
        install_command: Guidance command for installing the required dependency.

    Notes/Architectural Intent:
        Provides clear, actionable remediation messages for missing optional extras.
    """

    def __init__(self, extra_name: str, install_command: str) -> None:
        self.extra_name = extra_name
        self.install_command = install_command
        msg = (
            f"Optional extra '{extra_name}' is not installed. "
            f"Install it via: {install_command}"
        )
        super().__init__(msg)


__all__ = [
    "AdapterNotAvailableError",
    "ComplexityExceededError",
    "ParityViolationError",
    "QualityError",
    "QualityGateFailedError",
    "StatementIntegrityError",
]
