from types import ModuleType
from typing import Any, cast

from hexastack_core.infra.autodiscovery import (
    scan_modules,
)


def test_scan_modules_empty_inputs_noop():
    # Empty visitors
    scan_modules(["non_existent_package"], [])

    # Empty packages
    scan_modules([], [lambda m, mod: None])

    # Unimportable package handled gracefully
    scan_modules(["completely_invalid_package_xyz_123"], [lambda m, mod: None])


def test_scan_modules_invokes_visitors():
    mod = ModuleType("dummy_sample_module")

    class SampleClass:
        pass

    def sample_func():
        pass

    cast("Any", mod).SampleClass = SampleClass
    cast("Any", mod).sample_func = sample_func

    discovered_members: list[Any] = []

    def visitor(member: Any, module: ModuleType) -> None:
        discovered_members.append(member)

    scan_modules([mod], [visitor])

    assert SampleClass in discovered_members
    assert sample_func in discovered_members
