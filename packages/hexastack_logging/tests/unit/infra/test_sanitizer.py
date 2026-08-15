import pytest
from inline_snapshot import snapshot
from pydantic import BaseModel

from hexastack_logging.infra.sanitizer import Sanitizer


class UserModel(BaseModel):
    username: str
    password: str
    token: str


@pytest.mark.snapshot
def test_sanitizer_nested_dict():
    sanitizer = Sanitizer(
        masked_keys=["password", "secret", "cvv"],
        mask_replacement="[REDACTED]",
    )

    data = {
        "user": {
            "name": "Alice",
            "PASSWORD": "my_secret_pwd",
            "metadata": {
                "secrets": [{"secret": "sub-secret-123"}, {"public_id": "999"}],
                "cvv": 123,
            },
        }
    }

    assert sanitizer.sanitize_dict(data) == snapshot(
        {
            "user": {
                "name": "Alice",
                "PASSWORD": "[REDACTED]",
                "metadata": {
                    "secrets": [{"secret": "[REDACTED]"}, {"public_id": "999"}],
                    "cvv": "[REDACTED]",
                },
            }
        }
    )


@pytest.mark.snapshot
def test_sanitizer_pydantic_model():
    sanitizer = Sanitizer()
    user = UserModel(username="bob", password="supersecretpassword", token="tok123")

    assert sanitizer.sanitize(user) == snapshot(
        {"username": "bob", "password": "***REDACTED***", "token": "***REDACTED***"}
    )


def test_sanitizer_string_patterns():
    sanitizer = Sanitizer()

    # Bearer token regex test
    msg = "Authorization header received: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def successfully"
    scrubbed = sanitizer.sanitize_string(msg)
    assert "eyJhbGciOiJIUzI1NiJ9.abc.def" not in scrubbed
    assert "***REDACTED***" in scrubbed

    # Credit card regex test
    cc_msg = "Card number 4111 2222 3333 4444 charged"
    scrubbed_cc = sanitizer.sanitize_string(cc_msg)
    assert "4111 2222 3333 4444" not in scrubbed_cc
    assert "***REDACTED***" in scrubbed_cc


def test_sanitizer_traceback():
    sanitizer = Sanitizer()
    tb = """
    Traceback (most recent call last):
      File "auth.py", line 12, in login
        authenticate(token="Bearer secret-token-xyz-123")
    ValueError: Invalid Bearer secret-token-xyz-123
    """
    scrubbed_tb = sanitizer.sanitize_traceback(tb)
    assert "secret-token-xyz-123" not in scrubbed_tb
    assert "***REDACTED***" in scrubbed_tb
