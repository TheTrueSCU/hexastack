"""RFC 6901 JSON Pointer evaluation and manipulation utilities.

Notes/Architectural Intent:
    Provides deterministic RFC 6901 pointer resolution and mutation for
    nested configuration overrides, CQRS step input/output plumbing, and
    partial document patching without bespoke dictionary traversal logic.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from hexastack_core.domain.exceptions import PointerResolutionError

_DEFAULT = object()


def escape_pointer(segment: str) -> str:
    """Escape a JSON pointer reference segment according to RFC 6901.

    Args:
        segment: Raw property key or segment string.

    Returns:
        Escaped reference segment with '~' replaced by '~0' and '/' by '~1'.
    """
    return segment.replace("~", "~0").replace("/", "~1")


def unescape_pointer(segment: str) -> str:
    """Unescape a JSON pointer reference segment according to RFC 6901.

    Args:
        segment: Escaped reference segment string.

    Returns:
        Unescaped property key with '~1' replaced by '/' and '~0' by '~'.
    """
    return segment.replace("~1", "/").replace("~0", "~")


def _split_pointer(pointer: str) -> list[str]:
    """Parse and unescape reference segments from an RFC 6901 pointer string."""
    if not pointer:
        return []
    if not pointer.startswith("/"):
        msg = f"RFC 6901 pointer must start with '/', got {pointer!r}"
        raise PointerResolutionError(msg)
    raw_segments = pointer[1:].split("/")
    return [unescape_pointer(seg) for seg in raw_segments]


def _resolve_mapping_step(
    current: Mapping[str, Any],
    segment: str,
    default: Any,
    pointer: str,
    idx: int,
) -> Any:
    """Resolve a single segment against a Mapping container."""
    if segment in current:
        return current[segment]
    if default is not _DEFAULT:
        return default
    msg = f"Key {segment!r} not found at pointer segment {idx} in {pointer!r}"
    raise PointerResolutionError(msg)


def _resolve_sequence_step(
    current: Sequence[Any],
    segment: str,
    default: Any,
    pointer: str,
    idx: int,
) -> Any:
    """Resolve a single segment against a Sequence container."""
    try:
        list_idx = int(segment)
        if list_idx < 0:
            msg = f"Negative list index {list_idx} prohibited in RFC 6901: {pointer!r}"
            raise PointerResolutionError(msg)
        return current[list_idx]
    except (ValueError, IndexError) as err:
        if default is not _DEFAULT:
            return default
        msg = f"Invalid list index {segment!r} at segment {idx} in {pointer!r}: {err}"
        raise PointerResolutionError(msg) from err


def resolve_pointer(doc: Any, pointer: str, default: Any = _DEFAULT) -> Any:
    """Resolve an RFC 6901 pointer against a document.

    Args:
        doc: Source document (typically dict, list, or mapping).
        pointer: RFC 6901 pointer string (e.g. '/users/0/name').
        default: Optional fallback returned if target path does not exist.

    Returns:
        Resolved value at the specified pointer path.

    Raises:
        PointerResolutionError: If the pointer cannot be resolved and no default is provided.
    """
    if not isinstance(pointer, str):
        msg = f"Pointer must be a string, got {type(pointer).__name__}"
        raise PointerResolutionError(msg)

    if not pointer:
        return doc

    segments = _split_pointer(pointer)
    current = doc

    for idx, seg in enumerate(segments):
        if isinstance(current, Mapping):
            current = _resolve_mapping_step(current, seg, default, pointer, idx)
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes)):
            current = _resolve_sequence_step(current, seg, default, pointer, idx)
        else:
            if default is not _DEFAULT:
                return default
            msg = (
                f"Cannot traverse into non-container type {type(current).__name__} "
                f"at segment {idx} in {pointer!r}"
            )
            raise PointerResolutionError(msg)

    return current


def _navigate_intermediate(
    current: Any,
    segment: str,
    next_segment: str,
    idx: int,
) -> Any:
    """Navigate or dynamically instantiate intermediate container structures."""
    if isinstance(current, dict):
        if segment not in current or not isinstance(current[segment], (dict, list)):
            current[segment] = [] if next_segment.isdigit() else {}
        return current[segment]

    if isinstance(current, list):
        try:
            list_idx = int(segment)
            while len(current) <= list_idx:
                current.append([] if next_segment.isdigit() else {})
            return current[list_idx]
        except ValueError as err:
            msg = f"Invalid list index segment {segment!r}: {err}"
            raise PointerResolutionError(msg) from err

    msg = (
        f"Cannot traverse into non-container {type(current).__name__} at segment {idx}"
    )
    raise PointerResolutionError(msg)


def _set_terminal_value(current: Any, last_seg: str, value: Any) -> None:
    """Set the target value on the final container."""
    if isinstance(current, dict):
        current[last_seg] = value
        return

    if isinstance(current, list):
        if last_seg == "-":
            current.append(value)
            return
        try:
            list_idx = int(last_seg)
            while len(current) <= list_idx:
                current.append(None)
            current[list_idx] = value
            return
        except ValueError as err:
            msg = f"Invalid list index segment {last_seg!r}: {err}"
            raise PointerResolutionError(msg) from err

    msg = f"Cannot set value on non-container {type(current).__name__}"
    raise PointerResolutionError(msg)


def set_pointer(doc: Any, pointer: str, value: Any, inplace: bool = True) -> Any:
    """Set a value at the specified RFC 6901 pointer path.

    Args:
        doc: Target document (dict or list).
        pointer: RFC 6901 pointer string (e.g. '/config/timeout').
        value: New value to set at the destination.
        inplace: Whether to mutate target document directly (default: True).

    Returns:
        Mutated document with the value set.

    Raises:
        PointerResolutionError: If pointer is empty or path traversal is invalid.
    """
    if not isinstance(pointer, str) or not pointer:
        msg = "Pointer must be a non-empty string starting with '/'"
        raise PointerResolutionError(msg)

    segments = _split_pointer(pointer)
    target = doc if inplace else (dict(doc) if isinstance(doc, dict) else list(doc))
    current = target

    for idx, seg in enumerate(segments[:-1]):
        next_seg = segments[idx + 1]
        current = _navigate_intermediate(current, seg, next_seg, idx)

    _set_terminal_value(current, segments[-1], value)
    return target


def extract_pointers(doc: Any, prefix: str = "") -> list[str]:
    """Extract all valid RFC 6901 pointers contained within a document.

    Args:
        doc: Nested container document.
        prefix: Initial pointer prefix (defaults to '').

    Returns:
        List of all discovered RFC 6901 pointers.
    """
    pointers: list[str] = [prefix] if prefix else []

    if isinstance(doc, Mapping):
        for key, val in doc.items():
            child_ptr = f"{prefix}/{escape_pointer(str(key))}"
            pointers.extend(extract_pointers(val, child_ptr))
    elif isinstance(doc, Sequence) and not isinstance(doc, (str, bytes)):
        for idx, val in enumerate(doc):
            child_ptr = f"{prefix}/{idx}"
            pointers.extend(extract_pointers(val, child_ptr))

    return pointers


__all__ = [
    "escape_pointer",
    "extract_pointers",
    "resolve_pointer",
    "set_pointer",
    "unescape_pointer",
]
