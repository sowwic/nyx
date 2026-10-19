"""Conditions deciding whether an action is enabled.

A condition is a callable returning a bool that also announces when its answer
may have changed (`changed`). The `ActionRouter` listens to it, so widgets don't
have to refresh the actions by hand. Conditions combine with `&`, `|` and `~`.

Python's `and`, `or` and `not` can't be overloaded, and a condition object is
always truthy: combine conditions with the operators, never the keywords.
"""

import typing
from collections.abc import Callable

from PySide6 import QtCore


class ActionCondition(QtCore.QObject):
    """Base class of conditions. Subclasses implement `evaluate`.

    Attributes:
        changed: emitted when the result may have changed.
    """

    changed = QtCore.Signal()

    def __init__(self, description: str = "", parent: QtCore.QObject | None = None):
        """Initialize ActionCondition.

        Args:
            description (str): what has to be true, in a few words.
            parent (QtCore.QObject | None): parent object.
        """
        super().__init__(parent)
        self._description = description

    def __call__(self) -> bool:
        """bool: the condition is met right now."""
        return bool(self.evaluate())

    def __and__(self, other: Callable[[], bool]) -> ActionCondition:
        """Condition met when both conditions are met.

        Args:
            other (Callable[[], bool]): condition or plain callable.
        """
        return AllOf(self, as_condition(other))

    def __rand__(self, other: Callable[[], bool]) -> ActionCondition:
        return AllOf(as_condition(other), self)

    def __or__(self, other: Callable[[], bool]) -> ActionCondition:
        """Condition met when either condition is met.

        Args:
            other (Callable[[], bool]): condition or plain callable.
        """
        return AnyOf(self, as_condition(other))

    def __ror__(self, other: Callable[[], bool]) -> ActionCondition:
        return AnyOf(as_condition(other), self)

    def __invert__(self) -> ActionCondition:
        """Condition met when this one is not."""
        return Not(self)

    @property
    def description(self) -> str:
        """str: what has to be true, in a few words."""
        return self._description

    def evaluate(self) -> bool:
        """Check the condition. Subclasses must implement.

        Returns:
            bool: condition is met.
        """
        raise NotImplementedError

    def notify(self) -> None:
        """Announce that the result may have changed."""
        self.changed.emit()


class CallableCondition(ActionCondition):
    """Condition evaluated by calling a function.

    Pass the signals that can change the answer, and the condition follows them.
    """

    def __init__(
        self,
        function: Callable[[], bool],
        *signals: typing.Any,
        description: str = "",
        parent: QtCore.QObject | None = None,
    ):
        """Initialize CallableCondition.

        Args:
            function (Callable[[], bool]): returns whether the condition is met.
            *signals: Qt signals that invalidate the result.
            description (str): what has to be true, in a few words.
            parent (QtCore.QObject | None): parent object.
        """
        super().__init__(description, parent)
        self._function = function
        for signal in signals:
            signal.connect(self._on_source_changed)

    def evaluate(self) -> bool:
        """bool: result of the function."""
        return bool(self._function())

    def _on_source_changed(self, *_) -> None:
        """Pass on a change of one of the watched signals."""
        self.changed.emit()


class _Combination(ActionCondition):
    """Condition made of other conditions, changing when any of them changes."""

    JOINER = ""

    def __init__(self, *operands: ActionCondition):
        """Initialize the combination.

        Args:
            *operands (ActionCondition): conditions to combine.
        """
        super().__init__()
        self._operands = tuple(operands)
        for operand in self._operands:
            operand.changed.connect(self.changed)

    @property
    def operands(self) -> tuple[ActionCondition, ...]:
        """tuple[ActionCondition, ...]: combined conditions."""
        return self._operands

    @property
    def description(self) -> str:
        """str: descriptions of the operands, joined."""
        parts = [operand.description or "?" for operand in self._operands]
        return f"({self.JOINER.join(parts)})"


class AllOf(_Combination):
    """Condition met when all operands are met."""

    JOINER = " and "

    def evaluate(self) -> bool:
        """bool: every operand is met."""
        return all(operand() for operand in self._operands)


class AnyOf(_Combination):
    """Condition met when at least one operand is met."""

    JOINER = " or "

    def evaluate(self) -> bool:
        """bool: any operand is met."""
        return any(operand() for operand in self._operands)


class Not(_Combination):
    """Condition met when its operand is not."""

    def __init__(self, operand: ActionCondition):
        """Initialize Not.

        Args:
            operand (ActionCondition): condition to negate.
        """
        super().__init__(operand)

    @property
    def description(self) -> str:
        """str: description of the operand, negated."""
        return f"not {self._operands[0].description or '?'}"

    def evaluate(self) -> bool:
        """bool: the operand is not met."""
        return not self._operands[0]()


def as_condition(condition: Callable[[], bool] | ActionCondition) -> ActionCondition:
    """Turn a plain callable into a condition.

    Args:
        condition (Callable[[], bool] | ActionCondition): condition or callable.

    Returns:
        ActionCondition: the condition itself, or one calling the callable.
    """
    if isinstance(condition, ActionCondition):
        return condition
    return CallableCondition(condition)
