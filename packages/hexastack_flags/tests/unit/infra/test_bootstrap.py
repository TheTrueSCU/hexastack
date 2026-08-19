from hexastack_flags.adapters.openfeature import OpenFeatureFlagAdapter
from hexastack_flags.infra.bootstrap import FeatureFlagBootstrapper

from hexastack_core.infra.bootstrap import bootstrap
from hexastack_core.ports.feature_flags import FeatureFlagPort


def test_feature_flags_bootstrapper_registration():
    bootstrapper = FeatureFlagBootstrapper()
    assert bootstrapper.name == "feature_flags"
    assert bootstrapper.order == 14

    runtime = bootstrap(
        bootstrappers=[bootstrapper],
        auto_discover=False,
    )

    resolved_adapter = runtime.container.resolve(FeatureFlagPort)
    assert isinstance(resolved_adapter, OpenFeatureFlagAdapter)
