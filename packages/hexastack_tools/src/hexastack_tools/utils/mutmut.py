"""Pure mutant classification and syntactic heuristic utilities for mutmut.

Notes/Architectural Intent:
    Provides heuristic classification of surviving mutants into Critical, Equivalent,
    or Ignorable categories without dependencies on SQLite caches, subprocesses, or presenters.
"""

from __future__ import annotations

import re

__all__ = [
    "classify_mutant_line",
]


def classify_mutant_line(line_str: str, filename: str) -> tuple[str, str]:
    """Classify a surviving mutant based on syntactic and contextual heuristics.

    Args:
        line_str: Raw line of source code where mutation survived.
        filename: Path of the source file.

    Returns:
        Tuple of (category_string, rationale_string), where category is one of
        CRITICAL, EQUIVALENT, or IGNORABLE.

    Notes/Architectural Intent:
        Separates high-risk actionable business logic and security mutations from
        ignorable cosmetic, logging, or equivalent metadata changes.
    """
    stripped = line_str.strip()

    # 1. Ignorable test harnesses & demo recordings
    if "/testing/" in filename or "/devtools/" in filename or "recorder.py" in filename:
        return "IGNORABLE", "Test harness / demo recorder"

    # 2. Ignorable logging & terminal UI print statements
    if re.search(r"\b(?:logger|log)\.(?:debug|info|trace|warning|error)\(", stripped):
        return "IGNORABLE", "Log statement format"
    if re.search(r"\b(?:typer\.echo|console\.print|print)\(", stripped):
        return "IGNORABLE", "CLI / Console output"

    # 3. Ignorable docstrings / help metadata
    if re.search(r"\b(?:help|description|summary|instructions)\s*=", stripped):
        return "IGNORABLE", "Doc / Help text"
    if re.search(r":\s*(?:bool|str|int|float|list|dict|set)[^=]*=\s*Field\(", stripped):
        return "IGNORABLE", "Pydantic Field metadata"

    # 4. Equivalent candidates (dict fallbacks, default kwargs, None defaults, dataclass metadata)
    if re.search(r"@dataclass\(", stripped):
        return "EQUIVALENT", "Dataclass decorator configuration"
    if re.search(r":\s*[^=]+=\s*None\b", stripped):
        return "EQUIVALENT", "Model / dataclass default None attribute"
    if re.search(r"\.get\([^,]+,\s*None\)", stripped):
        return "EQUIVALENT", "Dict fallback with None default"
    if re.search(r"=\s*None\s*\)", stripped) or re.search(r"=\s*None\s*,", stripped):
        return "EQUIVALENT", "Optional parameter None default"
    if re.search(r"\bcast\(", stripped):
        return "EQUIVALENT", "Type casting statement"

    # 5. Critical / Actionable (Branch conditions, error mapping, security, state changes)
    if re.search(r"\b(?:if|elif|while|return|raise|assert)\b", stripped):
        return "CRITICAL", "Control flow / branching / assertion"
    if re.search(
        r"\b(?:status|error|exception|retry|auth|token|security)\b",
        stripped,
        re.IGNORECASE,
    ):
        return "CRITICAL", "Domain status / security / error handling"
    if re.search(r"[+\-*/%<>=!&|^]", stripped):
        return "CRITICAL", "Arithmetic / Comparison / Logical operator"

    return "CRITICAL", "Domain execution logic"
