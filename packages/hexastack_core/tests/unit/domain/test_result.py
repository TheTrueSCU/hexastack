
from hexastack_core.domain import Result


def test_ok():
    res = Result.ok(data="test_data")
    assert res.success is True
    assert res.data == "test_data"
    assert res.error_code is None


def test_error():
    res = Result.error(code="ERR_01", message="something went wrong")
    assert res.success is False
    assert res.error_code == "ERR_01"
    assert res.message == "something went wrong"
