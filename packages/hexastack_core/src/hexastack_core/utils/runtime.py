"""Runtime environment detection and edge execution profiles for Hexastack.

Notes/Architectural Intent:
    Provides standardized platform inspection distinguishing standard server runtimes
    (CPython, PyPy) from resource-constrained execution environments such as WebAssembly
    (Pyodide, Node.js WASI) and MicroPython. Allows hexagonal adapters and pipelines
    to automatically select zero-C-extension execution strategies and cooperative concurrency.
"""

from __future__ import annotations

import gc
import sys
from enum import StrEnum
from typing import Any


class RuntimeProfile(StrEnum):
    """Execution profile describing the underlying Python interpreter and host environment.

    Notes/Architectural Intent:
        Drives conditional feature enablement, selecting lightweight pure-Python
        fallbacks in constrained WASM and MicroPython targets without performance penalty
        on standard server deployments.
    """

    EMBEDDED = "embedded"
    STANDARD = "standard"
    WASM = "wasm"


def is_wasm() -> bool:
    """Return True if executing within a WebAssembly runtime (Pyodide, Emscripten, WASI).

    Returns:
        True if running in a WebAssembly environment, False otherwise.

    Notes/Architectural Intent:
        Detects Emscripten and WASI platforms via sys.platform and Pyodide module registration.
    """
    if sys.platform in {"emscripten", "wasi"}:
        return True
    if hasattr(sys, "_emscripten_info"):
        return True
    return "pyodide" in sys.modules


def is_micropython() -> bool:
    """Return True if executing within a MicroPython or CircuitPython interpreter.

    Returns:
        True if running under MicroPython, False otherwise.

    Notes/Architectural Intent:
        Inspects sys.implementation.name to identify embedded micro-controllers and IoT targets.
    """
    impl_name = getattr(sys.implementation, "name", "")
    return impl_name in {"micropython", "circuitpython"} or "micropython" in sys.modules


def is_edge() -> bool:
    """Return True if executing in an edge, browser, or resource-constrained embedded profile.

    Returns:
        True if running in WASM or MicroPython, False otherwise.
    """
    return is_wasm() or is_micropython()


def supports_threads() -> bool:
    """Return True if the active runtime supports OS threads and thread-pool offloading.

    Returns:
        False if thread creation is blocked or unsupported (typical for single-threaded WASM/MicroPython),
        True on standard multithreaded runtimes.
    """
    if is_edge():
        return False
    try:
        import threading

        return bool(threading.active_count() >= 1)
    except (ImportError, AttributeError):
        return False


def get_runtime_profile() -> RuntimeProfile:
    """Determine the active RuntimeProfile of the executing host.

    Returns:
        RuntimeProfile.WASM, RuntimeProfile.EMBEDDED, or RuntimeProfile.STANDARD.
    """
    if is_wasm():
        return RuntimeProfile.WASM
    if is_micropython():
        return RuntimeProfile.EMBEDDED
    return RuntimeProfile.STANDARD


def get_memory_footprint() -> dict[str, Any]:
    """Retrieve runtime memory usage statistics for diagnostics and profiling.

    Returns:
        Dictionary reporting total collected objects, garbage collection thresholds,
        and platform-specific metrics.

    Notes/Architectural Intent:
        Provides non-intrusive memory metrics across both standard CPython (via gc and resource)
        and embedded environments without hard dependencies on psutil.
    """
    stats: dict[str, Any] = {
        "tracked_objects": len(gc.get_objects()) if hasattr(gc, "get_objects") else 0,
        "profile": str(get_runtime_profile()),
    }

    if hasattr(gc, "get_count"):
        stats["gc_count"] = gc.get_count()

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        stats["max_rss_kb"] = usage.ru_maxrss
    except (ImportError, AttributeError):
        pass

    return stats


__all__ = [
    "get_memory_footprint",
    "get_runtime_profile",
    "is_edge",
    "is_micropython",
    "is_wasm",
    "RuntimeProfile",
    "supports_threads",
]
