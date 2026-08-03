from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


_FLOAT_TOLERANCE = Decimal("1e-6")


def outputs_match(expected: str, actual: str) -> bool:
    """Compare contest outputs token by token.

    The comparison follows the lightweight behavior used in moorepair: whitespace
    is insignificant, integers and decimals are compared numerically, and other
    tokens are compared exactly.
    """

    expected_tokens = expected.strip().split()
    actual_tokens = actual.strip().split()
    if len(expected_tokens) != len(actual_tokens):
        return False
    return all(_token_equal(exp, out) for exp, out in zip(expected_tokens, actual_tokens))


def _token_equal(left: str, right: str) -> bool:
    left_value = _parse_value(left)
    right_value = _parse_value(right)
    left_decimal = _to_decimal(left_value)
    right_decimal = _to_decimal(right_value)
    if left_decimal is not None and right_decimal is not None:
        if isinstance(left_value, Decimal) or isinstance(right_value, Decimal):
            scale = max(abs(left_decimal), abs(right_decimal), Decimal(1))
            return abs(left_decimal - right_decimal) <= _FLOAT_TOLERANCE * scale
        return left_decimal == right_decimal
    return left == right


def _parse_value(token: str) -> Any:
    lowered = token.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        if "." not in token and "e" not in lowered:
            return int(token, 10)
    except ValueError:
        pass
    try:
        value = Decimal(token)
        return value if value.is_finite() else token
    except (InvalidOperation, ValueError):
        return token


def _to_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool):
        return Decimal(1 if value else 0)
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, Decimal):
        return value
    return None
