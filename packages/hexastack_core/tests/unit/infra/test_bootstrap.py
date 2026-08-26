from hexastack_core.infra.bootstrap import (
    BootstrapContext,
    bootstrap,
)
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort


class ExtensionA(BootstrapperPort):
    name = "ext_a"
    order = 10

    def __init__(self) -> None:
        self.config_registered = False
        self.configured = False

    def configure(self, context: BootstrapContext) -> None:
        self.configured = True
        context.properties["ext_a_ran"] = True

    def register_config(self, registry: ConfigRegistry) -> None:
        self.config_registered = True


class ExtensionB(BootstrapperPort):
    name = "ext_b"
    order = 20

    def __init__(self) -> None:
        self.config_registered = False
        self.configured = False

    def configure(self, context: BootstrapContext) -> None:
        self.configured = True
        context.properties["ext_b_ran"] = True

    def register_config(self, registry: ConfigRegistry) -> None:
        self.config_registered = True


def test_core_meta_bootstrap():
    ext_a = ExtensionA()
    ext_b = ExtensionB()

    configured_called = False

    def hook(di):
        nonlocal configured_called
        configured_called = True

    res = bootstrap(
        bootstrappers=[ext_b, ext_a],
        auto_discover=False,
        configure_container=hook,
    )

    assert configured_called is True
    assert ext_a.config_registered is True
    assert ext_a.configured is True
    assert ext_b.config_registered is True
    assert ext_b.configured is True

    # Order should have sorted ext_a (order=10) before ext_b (order=20)
    assert res.bootstrappers == [ext_a, ext_b]
    assert res.get("ext_a_ran") is True
    assert res.get("ext_b_ran") is True

    # FeatureFlagPort should be registered in container
    from hexastack_core.ports.feature_flags import FeatureFlagPort

    assert FeatureFlagPort in res.container
    flags = res.container.resolve(FeatureFlagPort)
    assert flags.is_enabled("features.lib.pydantic") is True


def test_core_bootstrap_with_config_file(tmp_path):
    config_file = tmp_path / "hexastack.toml"
    config_file.write_text(
        '[hexastack]\napp_name = "BootstrapApp"\nenvironment = "prod"\n'
    )

    res = bootstrap(
        config_path=config_file,
        bootstrappers=[],
        auto_discover=True,
    )
    assert res.config is not None
    assert res.config._core.app_name == "BootstrapApp"
