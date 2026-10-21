import pytest

from nyx.plugins.functions import logic_operations as logic
from nyx.plugins.functions import math_operations as ops


@pytest.mark.parametrize(
    "func, args, expected",
    [
        (ops.add, (1, 2), 3),
        (ops.subtract, (5, 3), 2),
        (ops.multiply, (4, 2.5), 10),
        (ops.divide, (9, 2), 4.5),
        (ops.floor_divide, (9, 2), 4),
        (ops.modulo, (9, 4), 1),
        (ops.negate, (3,), -3),
        (ops.absolute, (-3,), 3),
        (ops.sign, (-7,), -1),
        (ops.sign, (0,), 0),
        (ops.sign, (7,), 1),
        (ops.minimum, (1, 2), 1),
        (ops.maximum, (1, 2), 2),
        (ops.clamp, (5, 0, 1), 1),
        (ops.clamp, (-5, 0, 1), 0),
        (ops.clamp, (0.5, 0, 1), 0.5),
        (ops.lerp, (10, 20, 0.25), 12.5),
        (ops.remap, (5, 0, 10, 0, 100), 50),
        (ops.average, (2, 4), 3),
        (ops.is_even, (4,), True),
        (ops.is_even, (3,), False),
    ],
)
def test_math_operations(func, args, expected):
    assert func(*args) == expected


def test_divide_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        ops.divide(1, 0)


@pytest.mark.parametrize(
    "func, args, expected",
    [
        (logic.is_equal, (1, 1.0), True),
        (logic.is_equal, ("a", "b"), False),
        (logic.is_not_equal, (1, 2), True),
        (logic.is_same, (None, None), True),
        (logic.is_same, ([], []), False),
        (logic.is_none, (None,), True),
        (logic.is_none, (0,), False),
        (logic.is_instance, (1, int), True),
        (logic.is_instance, ("a", int), False),
        (logic.is_instance, ("a", (int, str)), True),
        (logic.is_in, (1, [1, 2]), True),
        (logic.is_in, ("x", "abc"), False),
        (logic.greater_than, (2, 1), True),
        (logic.greater_than, (1, 1), False),
        (logic.greater_or_equal, (1, 1), True),
        (logic.less_than, (1, 2), True),
        (logic.less_or_equal, (2, 2), True),
        (logic.logical_and, (True, False), False),
        (logic.logical_or, (True, False), True),
        (logic.logical_xor, (True, True), False),
        (logic.logical_xor, (True, False), True),
        (logic.logical_not, (False,), True),
    ],
)
def test_logic_operations(func, args, expected):
    assert func(*args) is expected
