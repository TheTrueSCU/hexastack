import pytest

import hexastack as hs


def test_guaranteed_packages_present():
    """Verify guaranteed packages (core, cqrs, logging) are always exposed."""
    assert hs.core is not None
    assert hs.cqrs is not None
    assert hs.logging is not None

    # Verify architectural layers on guaranteed packages
    assert hs.core.domain is not None
    assert hs.core.ports is not None
    assert hs.core.infra is not None
    assert hs.core.adapters is not None
    assert hs.core.utils is not None

    assert hs.cqrs.domain is not None
    assert hs.cqrs.ports is not None
    assert hs.cqrs.infra is not None
    assert hs.cqrs.adapters is not None

    assert hs.logging.infra is not None
    assert hs.logging.adapters is not None


def test_installed_optional_packages_dynamically_available():
    """Verify optional packages in current workspace are available if installed."""
    import importlib.util

    for extra in ["events", "auth", "otel", "db", "fastapi"]:
        if importlib.util.find_spec(f"hexastack_{extra}") is not None:
            mod = getattr(hs, extra)
            assert mod is not None
            assert hasattr(mod, "infra") or hasattr(mod, "domain")


def test_uninstalled_package_error_message(monkeypatch):
    """Verify accessing an uninstalled optional package gives clear install instructions."""
    with pytest.raises(AttributeError) as exc_info:
        # Access a non-existent ecosystem package name
        _ = hs.__getattr__("nonexistent_package")
    assert "has no attribute 'nonexistent_package'" in str(exc_info.value)

    # Test known ecosystem package error message format
    with pytest.raises(AttributeError) as exc_info:
        _ = hs.__getattr__("ai")
    assert "Package 'hexastack-ai' is not installed" in str(exc_info.value)
    assert "pip install hexastack[ai]" in str(exc_info.value)
