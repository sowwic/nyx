import builtins
import dataclasses
import typing

from ..exceptions import DatatypeCastError
from ...static.enums import CoreDatatypes, GraphicsPlugShape


@dataclasses.dataclass(frozen=True)
class Datatype:
    """Describes the kind of value a node component holds.

    Datatypes are registered by plugins through `NyxPluginContents.datatypes`.
    Wildcard datatypes (e.g. `object`) are compatible with every other datatype.

    Attributes:
        type_id: unique id, namespaced by the providing plugin
        display_name: name shown in the UI
        color: plug color as a hex string
        plug_shape: shape of the plugs of components with the datatype
        caster: converts an evaluated value, raises on failure
        python_type: python type of values of this datatype, used to infer the
            datatype of a value
        default_factory: creates the value components of the datatype start with
        is_wildcard: compatible with every datatype
        compatible_with: type ids of the other datatypes it is compatible with
        selectable: can be picked by the user as the datatype of a component, false
            for datatypes that belong to a specific component type
    """

    type_id: str
    display_name: str
    color: str
    caster: typing.Callable[[typing.Any], typing.Any] = lambda value: value
    python_type: type | None = None
    plug_shape: GraphicsPlugShape = GraphicsPlugShape.CIRCLE
    default_factory: typing.Callable[[], typing.Any] = lambda: None
    is_wildcard: bool = False
    compatible_with: frozenset[str] = frozenset()
    selectable: bool = True

    def create_default(self) -> typing.Any:
        """Create the default value of the datatype.

        Returns:
            typing.Any: new default value, None for datatypes without one.
        """
        return self.default_factory()

    def cast(self, value: typing.Any) -> typing.Any:
        """Convert a value to this datatype.

        Args:
            value (typing.Any): evaluated value.

        Raises:
            DatatypeCastError: the value can't be converted.

        Returns:
            typing.Any: converted value.
        """
        try:
            return self.caster(value)
        except Exception as err:
            raise DatatypeCastError(
                f"Can't cast {value!r} to {self.display_name}: {err}"
            ) from err

    def matches(self, value: typing.Any) -> bool:
        """Check whether a value is exactly of the python type of this datatype.

        Args:
            value (typing.Any): value to check.

        Returns:
            bool: value matches. Exact types are compared so `bool` isn't an `int`.
        """
        return self.python_type is not None and type(value) is self.python_type

    def accepts(self, other: Datatype) -> bool:
        """Check whether a value of another datatype can be given to this one.

        Args:
            other (Datatype): datatype of the provided value.

        Returns:
            bool: datatypes are compatible.
        """
        return (
            self.is_wildcard
            or other.is_wildcard
            or self.type_id == other.type_id
            or other.type_id in self.compatible_with
        )


OBJECT_DATATYPE = Datatype(
    type_id=CoreDatatypes.OBJECT,
    display_name="Object",
    color="#0096FF",
    is_wildcard=True,
    plug_shape=GraphicsPlugShape.SQUARE_MATRIX,
)
"""Datatype of values without a type hint, used wherever no datatype is set."""


def value_to_class_name(value: typing.Any) -> typing.Any:
    """Turn a class into text that can be shown, edited and saved.

    Classes can't be written to a file or shown by the QML views, other values are
    fine as they are.

    Args:
        value (typing.Any): value of a component.

    Returns:
        typing.Any: the name of the class, qualified with its module unless it is a
            builtin one. Anything that isn't a class as it is.
    """
    if not isinstance(value, type):
        return value
    if getattr(builtins, value.__name__, None) is value:
        return value.__name__
    return f"{value.__module__}.{value.__qualname__}"


def value_to_view_text(value: typing.Any) -> typing.Any:
    """Turn a value into text the views can show and the user can edit.

    The QML views get lists and dictionaries as JavaScript objects, which they can only
    show as "[object Object]". As text they can be edited, text typed for a component
    is evaluated as a python expression when it is set.

    Args:
        value (typing.Any): value of a component.

    Returns:
        typing.Any: classes as their name, collections as python literals, anything
            else as it is.
    """
    if isinstance(value, (list, dict, tuple, set, frozenset)):
        return repr(value)
    return value_to_class_name(value)
