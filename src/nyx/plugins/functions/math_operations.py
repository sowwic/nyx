"""Basic math functions missing from python's `math` module."""


def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


def divide(a: float, b: float) -> float:
    """Divide a by b."""
    return a / b


def floor_divide(a: float, b: float) -> float:
    """Divide a by b, rounding down."""
    return a // b


def modulo(a: float, b: float) -> float:
    """Get the remainder of dividing a by b."""
    return a % b


def negate(value: float) -> float:
    """Flip the sign of a number."""
    return -value


def absolute(value: float) -> float:
    """Get the distance of a number from zero."""
    return abs(value)


def sign(value: float) -> int:
    """Get -1, 0 or 1 for a negative, zero or positive number."""
    return (value > 0) - (value < 0)


def minimum(a: float, b: float) -> float:
    """Get the smaller of two numbers."""
    return min(a, b)


def maximum(a: float, b: float) -> float:
    """Get the bigger of two numbers."""
    return max(a, b)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Limit a number to the range from low to high."""
    return max(low, min(value, high))


def lerp(a: float, b: float, t: float = 0.5) -> float:
    """Interpolate linearly from a to b, t=0 gives a and t=1 gives b."""
    return a + (b - a) * t


def remap(
    value: float,
    from_low: float = 0.0,
    from_high: float = 1.0,
    to_low: float = 0.0,
    to_high: float = 1.0,
) -> float:
    """Move a number from one range to another."""
    return to_low + (value - from_low) * (to_high - to_low) / (from_high - from_low)


def average(a: float, b: float) -> float:
    """Get the mean of two numbers."""
    return (a + b) / 2


def is_even(value: int) -> bool:
    """Check if a whole number is even."""
    return value % 2 == 0
