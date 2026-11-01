import pytest
from inline_snapshot import snapshot
from pydantic import BaseModel

from hexastack_logging.utils.sanitizer import LogSanitizer


class UserModel(BaseModel):
    username: str
    password: str
    token: str


def test_log_sanitizer_data_structures():
    sanitizer = LogSanitizer()

    # 1. Tuples
    tup = ("Alice", "Bearer eyJhbGci.secret", 123)
    san_tup = sanitizer.sanitize(tup)
    assert isinstance(san_tup, tuple)
    assert san_tup[0] == "Alice"
    assert san_tup[1] == "***REDACTED***"
    assert san_tup[2] == 123

    # 2. Sets
    s = {"Bearer secret-token-abc", 42}
    san_s = sanitizer.sanitize(s)
    assert isinstance(san_s, set)
    assert "***REDACTED***" in san_s
    assert 42 in san_s

    # 3. Integers/Primitives (passthrough)
    assert sanitizer.sanitize(12345) == 12345
    assert sanitizer.sanitize(None) is None
    assert sanitizer.sanitize(True) is True

    # 4. Dict containing Pydantic models and nested lists of strings
    nested = {
        "user": UserModel(username="charlie", password="pwd", token="tok"),
        "raw_tokens": ["Bearer token1", "Bearer token2"],
        "info": "plain text with Bearer abc",
        "num": 999,
        "nested_dict": {
            "secret_key": "api_key_12345",  # pragma: allowlist secret
            "api_key": "raw_secret",  # pragma: allowlist secret
            "sub": {"token": "inner_token", "normal": "value"},
        },
    }
    san_nested = sanitizer.sanitize_dict(nested)
    assert san_nested["user"] == {
        "username": "charlie",
        "password": "***REDACTED***",
        "token": "***REDACTED***",
    }
    assert san_nested["raw_tokens"] == ["***REDACTED***", "***REDACTED***"]
    assert san_nested["info"] == "plain text with ***REDACTED***"
    assert san_nested["num"] == 999
    assert san_nested["nested_dict"] == {
        "secret_key": "api_key_12345",  # pragma: allowlist secret
        "api_key": "***REDACTED***",
        "sub": {"token": "***REDACTED***", "normal": "value"},
    }


@pytest.mark.snapshot
def test_log_sanitizer_nested_dict():
    sanitizer = LogSanitizer(
        masked_keys=["password", "secret", "cvv"],
        mask_replacement="[REDACTED]",
    )

    data = {
        "user": {
            "name": "Alice",
            "PASSWORD": "my_secret_pwd",  # pragma: allowlist secret
            "metadata": {
                "secrets": [
                    {"secret": "sub-secret-123"},  # pragma: allowlist secret
                    {"public_id": "999"},
                ],
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
def test_log_sanitizer_pydantic_model():
    sanitizer = LogSanitizer()
    user = UserModel(
        username="bob",
        password="supersecretpassword",  # pragma: allowlist secret
        token="tok123",
    )

    assert sanitizer.sanitize(user) == snapshot(
        {"username": "bob", "password": "***REDACTED***", "token": "***REDACTED***"}
    )


def test_log_sanitizer_string_patterns():
    sanitizer = LogSanitizer()

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


def test_log_sanitizer_traceback():
    sanitizer = LogSanitizer()
    tb = """
    Traceback (most recent call last):
      File "auth.py", line 12, in login
        authenticate(token="Bearer secret-token-xyz-123")
    ValueError: Invalid Bearer secret-token-xyz-123
    """
    scrubbed_tb = sanitizer.sanitize_traceback(tb)
    assert "secret-token-xyz-123" not in scrubbed_tb
    assert "***REDACTED***" in scrubbed_tb


def test_log_sanitizer_csp_and_cloud_credentials():
    sanitizer = LogSanitizer()

    # 1. AWS Access Key ID and Secret Access Key
    fake_aki = "".join(["AKIA", "IOSFODNN7EXAMPLE"])
    fake_sak = "".join(["wJalrXUtnFEMI/", "K7MDENG/bPxRfiCYEXAMPLEKEY"])
    aws_msg = f"Deploying with {fake_aki} and aws_secret_access_key='{fake_sak}'"
    scrubbed_aws = sanitizer.sanitize_string(aws_msg)
    assert fake_aki not in scrubbed_aws
    assert fake_sak not in scrubbed_aws
    assert "***REDACTED***" in scrubbed_aws

    # 2. GCP API Key
    fake_gcp = "".join(
        ["AIza", "SyD-1234567890abcdefghijklmnopqrst"]  # pragma: allowlist secret
    )
    gcp_msg = f"Google Maps API call failed with key {fake_gcp}"
    scrubbed_gcp = sanitizer.sanitize_string(gcp_msg)
    assert fake_gcp not in scrubbed_gcp
    assert "***REDACTED***" in scrubbed_gcp

    # 3. OCI Tenancy OCID and API Fingerprint
    fake_ocid = "".join(["ocid1.tenancy.oc1..", "aaaaaaaaba3pvsnwdop4odjhkeoi"])
    fake_fp = ":".join(
        [
            "12",
            "34",
            "56",
            "78",
            "90",
            "ab",
            "cd",
            "ef",
            "12",
            "34",
            "56",
            "78",
            "90",
            "ab",
            "cd",
            "ef",
        ]
    )
    oci_msg = f"Connecting to tenancy {fake_ocid} with fingerprint {fake_fp}"
    scrubbed_oci = sanitizer.sanitize_string(oci_msg)
    assert fake_ocid not in scrubbed_oci
    assert fake_fp not in scrubbed_oci
    assert "***REDACTED***" in scrubbed_oci

    # 4. GitHub Personal Access Token
    fake_ghp = "".join(
        ["ghp_", "1234567890abcdefghijklmnopqrstuvwxyzAB"]  # pragma: allowlist secret
    )
    gh_msg = f"Pushing to remote with token {fake_ghp}"
    scrubbed_gh = sanitizer.sanitize_string(gh_msg)
    assert fake_ghp not in scrubbed_gh
    assert "***REDACTED***" in scrubbed_gh

    # 5. Inline PEM Private Key Block (dynamically joined to prevent detect-private-key false positive)
    pem_begin = "".join(["-----", "BEGIN RSA ", "PRIVATE KEY-----"])
    pem_end = "".join(["-----", "END RSA ", "PRIVATE KEY-----"])
    pem_body = "".join(
        [
            "MIIEowIBAAKCAQEA0Y",
            "1234567890abcdefghijklmnopqrstuvwxyz",  # pragma: allowlist secret
        ]
    )
    pem_msg = f"Loaded key:\n{pem_begin}\n{pem_body}\n{pem_end}\nStatus: Ready"
    scrubbed_pem = sanitizer.sanitize_string(pem_msg)
    assert pem_body not in scrubbed_pem
    assert pem_begin not in scrubbed_pem
    assert "***REDACTED***" in scrubbed_pem

    # 6. Azure Account Key
    fake_az = "".join(
        [
            "abcdefghijklmnopqrstuvwxyz0123456789+/",
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn012==",  # pragma: allowlist secret
        ]
    )
    az_msg = f"Storage error with AccountKey={fake_az}"
    scrubbed_az = sanitizer.sanitize_string(az_msg)
    assert fake_az not in scrubbed_az
    assert "***REDACTED***" in scrubbed_az

    # 7. Dictionary with CSP and cloud key names
    csp_dict = {
        "access_key_id": "".join(
            ["AKIA", "1111111111EXAMPLE"]
        ),  # pragma: allowlist secret
        "secret_access_key": "raw-dummy-key-12345",  # pragma: allowlist secret
        "tenancy_ocid": "".join(["ocid1.tenancy.oc1..", "test"]),
        "user_ocid": "".join(["ocid1.user.oc1..", "testuser"]),
        "fingerprint": ":".join(
            [
                "aa",
                "bb",
                "cc",
                "dd",
                "ee",
                "ff",
                "00",
                "11",
                "22",
                "33",
                "44",
                "55",
                "66",
                "77",
                "88",
                "99",
            ]
        ),
        "client_secret": "dummy-azure-secret",  # pragma: allowlist secret
        "service_account_json": '{"type": "service_account"}',  # pragma: allowlist secret
        "webhook_secret": "whsec_abcdef123456",  # pragma: allowlist secret
        "normal_key": "safe_value",
    }
    sanitized_dict = sanitizer.sanitize_dict(csp_dict)
    assert sanitized_dict["access_key_id"] == "***REDACTED***"
    assert sanitized_dict["secret_access_key"] == "***REDACTED***"
    assert sanitized_dict["tenancy_ocid"] == "***REDACTED***"
    assert sanitized_dict["user_ocid"] == "***REDACTED***"
    assert sanitized_dict["fingerprint"] == "***REDACTED***"
    assert sanitized_dict["client_secret"] == "***REDACTED***"
    assert sanitized_dict["service_account_json"] == "***REDACTED***"
    assert sanitized_dict["webhook_secret"] == "***REDACTED***"
    assert sanitized_dict["normal_key"] == "safe_value"
