"""Basic comparison and boolean functions."""

import typing


def is_equal(a: typing.Any, b: typing.Any) -> bool:
    """Check if two values are equal."""
    return a == b


def is_not_equal(a: typing.Any, b: typing.Any) -> bool:
    """Check if two values are different."""
    return a != b


def is_same(a: typing.Any, b: typing.Any) -> bool:
    """Check if two values are the same object."""
    return a is b


def is_none(value: typing.Any) -> bool:
    """Check if a value is None."""
    return value is None


def is_instance(value: typing.Any, cls: typing.Any) -> bool:
    """Check if a value is an instance of a class, or of one in a tuple of classes."""
    return isinstance(value, cls)


def is_in(value: typing.Any, container: typing.Any) -> bool:
    """Check if a value is in a container."""
    return value in container


def greater_than(a: float, b: float) -> bool:
    """Check if a is bigger than b."""
    return a > b


def greater_or_equal(a: float, b: float) -> bool:
    """Check if a is bigger than or equal to b."""
    return a >= b


def less_than(a: float, b: float) -> bool:
    """Check if a is smaller than b."""
    return a < b


def less_or_equal(a: float, b: float) -> bool:
    """Check if a is smaller than or equal to b."""
    return a <= b


def logical_and(a: bool, b: bool) -> bool:
    """Check if both values are true."""
    return a and b


def logical_or(a: bool, b: bool) -> bool:
    """Check if any of the values is true."""
    return a or b


def logical_xor(a: bool, b: bool) -> bool:
    """Check if exactly one of the values is true."""
    return a != b


def logical_not(value: bool) -> bool:
    """Flip a boolean."""
    return not value
