from hypothesis import given
from hypothesis import strategies as st

from hexastack_core.domain import Result


@given(st.text(), st.text())
def test_error_roundtrip(code: str, message: str):
    res = Result.error(code=code, message=message)
    assert res.success is False
    assert res.error_code == code
    assert res.message == message


@given(st.integers() | st.text())
def test_ok_roundtrip(data: int | str):
    res = Result.ok(data=data)
    assert res.success is True
    assert res.data == data
