"""How much of the buggy program a returned program keeps, by tokens and by non-empty lines."""

from __future__ import annotations

import difflib
import io
import re
import tokenize

_IGNORED = {
    tokenize.ENCODING,
    tokenize.ENDMARKER,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.NEWLINE,
    tokenize.NL,
}


def _python_tokens(code: str) -> list[str]:
    try:
        return [
            token.string
            for token in tokenize.generate_tokens(io.StringIO(code).readline)
            if token.type not in _IGNORED and token.string.strip()
        ]
    except (IndentationError, tokenize.TokenError):
        return code.split()


def _java_tokens(code: str) -> list[str]:
    return re.findall(r"\w+|[^\w\s]", code)


def _lines(code: str) -> list[str]:
    return [line.strip() for line in code.splitlines() if line.strip()]


def _retained_fraction(source: list[str], candidate: list[str]) -> float:
    if not source:
        return 1.0 if not candidate else 0.0
    matcher = difflib.SequenceMatcher(None, source, candidate, autojunk=False)
    return sum(block.size for block in matcher.get_matching_blocks()) / len(source)


def retention(buggy_code: str, fixed_code: str, *, language: str = "python") -> dict[str, float]:
    tokens = _java_tokens if language == "java" else _python_tokens
    return {
        "token_retention": _retained_fraction(tokens(buggy_code), tokens(fixed_code)),
        "line_retention": _retained_fraction(_lines(buggy_code), _lines(fixed_code)),
    }
