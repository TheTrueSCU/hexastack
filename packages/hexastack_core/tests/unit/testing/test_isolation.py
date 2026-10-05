from hexastack_core.testing.isolation import (
    ClearableRegistry,
    isolate_registries,
)


class MockRegistry:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, item: str) -> None:
        self.items.append(item)

    def clear(self) -> None:
        self.items.clear()


def test_clearable_registry_protocol():
    reg = MockRegistry()
    assert isinstance(reg, ClearableRegistry)


def test_isolate_registries_clears_before_and_after():
    reg1 = MockRegistry()
    reg2 = MockRegistry()

    reg1.add("stale1")
    reg2.add("stale2")

    with isolate_registries(reg1, reg2):
        assert len(reg1.items) == 0
        assert len(reg2.items) == 0

        reg1.add("temp1")
        reg2.add("temp2")
        assert len(reg1.items) == 1
        assert len(reg2.items) == 1

    assert len(reg1.items) == 0
    assert len(reg2.items) == 0
