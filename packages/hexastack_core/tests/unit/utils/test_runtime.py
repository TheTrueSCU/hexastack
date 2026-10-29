"""Unit tests for runtime platform detection and edge profiling."""

import sys
from unittest.mock import MagicMock, patch

from hexastack_core.utils.runtime import (
    RuntimeProfile,
    get_memory_footprint,
    get_runtime_profile,
    is_edge,
    is_micropython,
    is_wasm,
    supports_threads,
)


def test_standard_cpython_detection():
    # In normal Linux/macOS test environment
    profile = get_runtime_profile()
    assert profile == RuntimeProfile.STANDARD
    wasm_flag = is_wasm()
    assert wasm_flag is False
    mpy_flag = is_micropython()
    assert mpy_flag is False
    edge_flag = is_edge()
    assert edge_flag is False
    threads_flag = supports_threads()
    assert threads_flag is True


def test_wasm_emscripten_and_wasi_detection():
    with patch("sys.platform", "emscripten"):
        res_emscripten = is_wasm()
        assert res_emscripten is True
        prof_emscripten = get_runtime_profile()
        assert prof_emscripten == RuntimeProfile.WASM
        assert is_edge() is True
        assert supports_threads() is False

    with patch("sys.platform", "wasi"):
        res_wasi = is_wasm()
        assert res_wasi is True
        prof_wasi = get_runtime_profile()
        assert prof_wasi == RuntimeProfile.WASM

    with patch.dict("sys.modules", {"pyodide": MagicMock()}):
        res_pyodide = is_wasm()
        assert res_pyodide is True

    # Simulate _emscripten_info attribute
    with patch.object(sys, "_emscripten_info", (3, 1, 45), create=True):
        res_info = is_wasm()
        assert res_info is True


def test_micropython_detection():
    mock_impl = MagicMock()
    mock_impl.name = "micropython"
    with patch("sys.implementation", mock_impl):
        res_mpy = is_micropython()
        assert res_mpy is True
        prof_mpy = get_runtime_profile()
        assert prof_mpy == RuntimeProfile.EMBEDDED
        assert is_edge() is True
        assert supports_threads() is False

    mock_circuit = MagicMock()
    mock_circuit.name = "circuitpython"
    with patch("sys.implementation", mock_circuit):
        res_circuit = is_micropython()
        assert res_circuit is True

    with patch.dict("sys.modules", {"micropython": MagicMock()}):
        res_mod = is_micropython()
        assert res_mod is True


def test_supports_threads_without_threading_module():
    with patch.dict("sys.modules", {"threading": None}):  # type: ignore[dict-item]
        # In an environment without threading
        res = supports_threads()
        assert res is False


def test_get_memory_footprint():
    stats = get_memory_footprint()
    assert isinstance(stats, dict)
    assert "tracked_objects" in stats
    assert "profile" in stats
    assert stats["profile"] in {p.value for p in RuntimeProfile}
