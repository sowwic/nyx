import typing
import logging

from ..static.enums import NodeComponentValueMask

if typing.TYPE_CHECKING:
    from .node_component import NodeComponent

LOGGER = logging.getLogger(__name__)


class ValueStorage:
    """Holds and evaluates the value of a node component.

    The raw, cached and display values live in the item data of the owning component,
    the storage decides how they are set, evaluated and displayed. Components select
    the storage class through `NodeComponent.VALUE_STORAGE_CLS`, so plugins can
    customize value behaviour without touching the component.
    """

    def __init__(self, component: NodeComponent):
        """Initialize ValueStorage.

        Args:
            component (NodeComponent): component the value belongs to.
        """
        self.component = component

    @property
    def raw_value(self) -> typing.Any:
        """typing.Any: value as set, before evaluation."""
        return self.component.data(self.component.Roles.RAW_VALUE)

    @property
    def cached_value(self) -> typing.Any:
        """typing.Any: evaluated value."""
        return self.component.data(self.component.Roles.CACHED_VALUE)

    @property
    def display_value(self) -> str:
        """str: value text shown in the UI."""
        return self.component.data(self.component.Roles.DISPLAY_VALUE)

    def set_raw_value(self, value: typing.Any) -> None:
        """Set the raw value, and the cached value to the same unevaluated value.

        Args:
            value (typing.Any): new raw value.
        """
        self.component.setData(value, role=self.component.Roles.RAW_VALUE)
        self.component.setData(value, role=self.component.Roles.CACHED_VALUE)

    def set_cached_value(self, value: typing.Any) -> None:
        """Set the cached value.

        Args:
            value (typing.Any): new cached value.
        """
        self.component.setData(value, role=self.component.Roles.CACHED_VALUE)

    def set_display_value(self, text: str) -> None:
        """Set the display value.

        Args:
            text (str): new display text.
        """
        self.component.setData(text, role=self.component.Roles.DISPLAY_VALUE)

    def push(self, value: typing.Any, evaluate: bool = True) -> None:
        """Set the value.

        Args:
            value (typing.Any): new raw value.
            evaluate (bool): evaluate the value after setting it.
        """
        self.set_raw_value(value)
        if evaluate:
            self.evaluate()
        self.refresh_display_value()

    def pull(self, value_mask: NodeComponentValueMask) -> typing.Any:
        """Get a value of the storage.

        Args:
            value_mask (NodeComponentValueMask): which value to get.

        Returns:
            typing.Any: requested value.
        """
        if value_mask is NodeComponentValueMask.RAW:
            return self.raw_value
        elif value_mask is NodeComponentValueMask.CACHE:
            return self.cached_value
        elif value_mask is NodeComponentValueMask.DISPLAY:
            return self.display_value
        else:
            raise ValueError(f"Invalid value mask: {value_mask}")

    def evaluate(self) -> None:
        """Evaluate the raw value and store the result as the cached value."""
        self.set_cached_value(self.compute_value())

    def compute_value(self) -> typing.Any:
        """Compute the evaluated value. Strings are evaluated as python expressions.

        Returns:
            typing.Any: evaluated value, the raw value if evaluation fails.
        """
        out_value = self.raw_value
        if isinstance(self.raw_value, str):
            try:
                out_value = eval(self.raw_value)
            except Exception:
                LOGGER.warning(f"Failed to eval {self.raw_value}, defaulting to str")
        return out_value

    def clear_cache(self) -> None:
        """Clear the cached value and reset the display value to the raw value."""
        self.set_cached_value(None)
        self.set_display_value(str(self.raw_value))

    def refresh_display_value(self) -> None:
        """Set the display value from the cached value."""
        self.set_display_value(str(self.cached_value))
