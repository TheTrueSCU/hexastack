from hexastack_core.adapters.feature_flags.in_memory import InMemoryFeatureFlagAdapter
from hexastack_core.testing.flags import require_extra, require_feature


def test_require_extra_installed():
    mark = require_extra("pydantic")
    # pydantic is installed, condition should be False (do not skip)
    assert mark.args[0] is False


def test_require_extra_missing():
    mark = require_extra("totally_fake_library_xyz")
    # fake library is not installed, condition should be True (skip)
    assert mark.args[0] is True
    assert (
        "Optional extra 'totally_fake_library_xyz' is not installed"
        in mark.kwargs["reason"]
    )


def test_require_feature_enabled():
    adapter = InMemoryFeatureFlagAdapter({"beta.search": True, "beta.chat": False})
    mark = require_feature("beta.search", flags=adapter)
    assert mark.args[0] is False


def test_require_feature_disabled():
    adapter = InMemoryFeatureFlagAdapter({"beta.search": True, "beta.chat": False})
    mark = require_feature("beta.chat", flags=adapter)
    assert mark.args[0] is True
    assert "Feature flag 'beta.chat' is disabled" in mark.kwargs["reason"]
