import string

from hypothesis import given
from hypothesis import strategies as st

from hexastack_cli.adapters.routing import _to_kebab_case


@given(
    words=st.lists(
        st.text(alphabet=string.ascii_letters, min_size=1, max_size=15),
        min_size=1,
        max_size=6,
    ),
    suffix=st.sampled_from(["Command", "Query", "Cmd", "Qry", ""]),
)
def test_to_kebab_case_invariants(words: list[str], suffix: str):
    # Form PascalCase name e.g. "CreateOrderUserCommand"
    pascal_name = "".join(w.capitalize() for w in words) + suffix
    kebab = _to_kebab_case(pascal_name)

    # Invariant 1: Output is always lower-case or contains digits/hyphens
    assert kebab == kebab.lower()

    # Invariant 2: No leading or trailing hyphens
    assert not kebab.startswith("-")
    assert not kebab.endswith("-")

    # Invariant 3: No double consecutive hyphens
    assert "--" not in kebab

    # Invariant 4: Does not end with raw suffix name
    if suffix in {"Command", "Query", "Cmd", "Qry"} and len(words) > 0:
        assert not kebab.endswith("-" + suffix.lower())
