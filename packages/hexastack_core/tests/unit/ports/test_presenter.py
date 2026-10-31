import inspect
from typing import Any

import pytest

from hexastack_core.domain.generic import Generic
from hexastack_core.ports.presenter import PresenterPort


class SampleOutput(Generic):
    text: str


class JsonPresenter(PresenterPort):
    def present(self, instance: Generic) -> Any | None:
        if isinstance(instance, SampleOutput):
            return {"formatted_text": instance.text}
        return None


def test_presenter_interface():
    presenter = JsonPresenter()
    output = SampleOutput(text="hello world")
    presented = presenter.present(output)

    assert presented == {"formatted_text": "hello world"}


def test_presenter_port_is_abstract() -> None:
    """Verify that PresenterPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(PresenterPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        PresenterPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_presenter_port_abstract_methods() -> None:
    """Verify abstract methods on PresenterPort."""
    expected = {"present"}
    abstracts = PresenterPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
