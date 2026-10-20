import dataclasses
import typing

from .exceptions import DatatypeCastError
from ..static.enums import CoreDatatypes


@dataclasses.dataclass(frozen=True)
class Datatype:
    """Describes the kind of value a node component holds.

    Datatypes are registered by plugins through `NyxPluginContents.datatypes`.
    Wildcard datatypes (e.g. `object`) are compatible with every other datatype.

    Attributes:
        type_id: unique id, namespaced by the providing plugin
        display_name: name shown in the UI
        color: plug color as a hex string
        caster: converts an evaluated value, raises on failure
        is_wildcard: compatible with every datatype
    """

    type_id: str
    display_name: str
    color: str
    caster: typing.Callable[[typing.Any], typing.Any] = lambda value: value
    is_wildcard: bool = False

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

    def accepts(self, other: Datatype) -> bool:
        """Check whether a value of another datatype can be given to this one.

        Args:
            other (Datatype): datatype of the provided value.

        Returns:
            bool: datatypes are compatible.
        """
        return self.is_wildcard or other.is_wildcard or self.type_id == other.type_id


OBJECT_DATATYPE = Datatype(
    type_id=CoreDatatypes.OBJECT,
    display_name="Object",
    color="#0096FF",
    is_wildcard=True,
)
"""Datatype of values without a type hint, used wherever no datatype is set."""
