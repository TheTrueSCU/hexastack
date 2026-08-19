from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from hexastack_logging.infra.sanitizer import Sanitizer

# Strategy producing arbitrary JSON-like recursive trees
json_primitives = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=30),
)

json_tree = st.recursive(
    json_primitives,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(min_size=1, max_size=15), children, max_size=5),
    ),
    max_leaves=15,
)


@given(
    token=st.from_regex(r"[A-Za-z0-9\-_~+/]{10,40}", fullmatch=True),
    prefix=st.text(max_size=20),
    suffix=st.text(max_size=20),
)
def test_sanitizer_bearer_pattern_invariant(token: str, prefix: str, suffix: str):
    sanitizer = Sanitizer(mask_replacement="***")
    input_str = f"{prefix} Bearer {token} {suffix}"
    scrubbed = sanitizer.sanitize(input_str)

    # Invariant: Token substring never appears in the output when prefixed with Bearer
    if token:
        assert f"Bearer {token}" not in scrubbed


@given(
    secret_key=st.sampled_from(
        ["password", "token", "secret", "api_key", "cvv", "access_token"]
    ),
    secret_val=st.text(min_size=1, max_size=40),
    other_data=json_tree,
)
def test_sanitizer_key_redaction_invariant(
    secret_key: str, secret_val: str, other_data: Any
):
    sanitizer = Sanitizer(mask_replacement="[PROTECTED]")
    payload = {
        secret_key: secret_val,
        secret_key.upper(): secret_val,
        "nested": {secret_key: secret_val, "safe": other_data},
    }

    sanitized = sanitizer.sanitize(payload)

    # Invariant 1: Top-level sensitive keys are always replaced
    assert sanitized[secret_key] == "[PROTECTED]"
    assert sanitized[secret_key.upper()] == "[PROTECTED]"

    # Invariant 2: Nested sensitive keys are always replaced
    assert sanitized["nested"][secret_key] == "[PROTECTED]"
