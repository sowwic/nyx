import typing
import logging

from .exceptions import DatatypeCastError
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
        self._cast_error: str | None = None

    @property
    def is_valid(self) -> bool:
        """bool: the last evaluated value could be cast to the component datatype."""
        return self._cast_error is None

    @property
    def cast_error(self) -> str | None:
        """str | None: why the last evaluated value couldn't be cast."""
        return self._cast_error

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
        if evaluate:
            self.component.setData(value, role=self.component.Roles.RAW_VALUE)
            self.evaluate()
        else:
            self.set_raw_value(value)
            self._set_cast_error(None)
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
        """Evaluate the raw value and store the result as the cached value.

        The value is cast to the component datatype. When that fails the previous
        cached value is kept and the storage becomes invalid.
        """
        try:
            self.set_cached_value(self.cast_value(self.compute_value()))
        except DatatypeCastError as err:
            LOGGER.warning(str(err))
            self._set_cast_error(str(err))
        else:
            self._set_cast_error(None)

    def cast_value(self, value: typing.Any) -> typing.Any:
        """Cast an evaluated value to the component datatype.

        A missing value (None) becomes the default of the datatype, if it has one.

        Args:
            value (typing.Any): evaluated value.

        Raises:
            DatatypeCastError: the value can't be converted.

        Returns:
            typing.Any: converted value.
        """
        datatype = self.component.datatype
        if value is None:
            value = datatype.create_default()
        if value is None:
            return None
        return datatype.cast(value)

    def _set_cast_error(self, error: str | None) -> None:
        """Store the cast error and notify the model when validity changed.

        Args:
            error (str | None): error message, None if the cast succeeded.
        """
        was_valid = self.is_valid
        self._cast_error = error
        model = self.component.model()
        if model is not None and was_valid != self.is_valid:
            model.dataChanged.emit(
                self.component.index(),
                self.component.index(),
                [self.component.Roles.IS_VALID],
            )

    def compute_value(self) -> typing.Any:
        """Compute the evaluated value. Strings are evaluated as python expressions.

        Returns:
            typing.Any: evaluated value, the raw value if evaluation fails.
        """
        out_value = self.raw_value
        if isinstance(self.raw_value, str) and self.raw_value:
            try:
                out_value = eval(self.raw_value)
            except Exception:
                pass
        return out_value

    def clear_cache(self) -> None:
        """Clear the cached value and reset the display value to the raw value."""
        self.set_cached_value(None)
        self.set_display_value(str(self.raw_value))

    def refresh_display_value(self) -> None:
        """Set the display value from the cached value."""
        self.set_display_value(str(self.cached_value))
