import pathlib
import typing

from nyx.api.v1 import (
    NYX_REGISTRY,
    CoreDatatypes,
    Datatype,
    GraphicsPlugShape,
    OBJECT_DATATYPE,
)


def cast_to_type_id(value: typing.Any) -> str:
    """Get the id of the datatype a value stands for.

    Args:
        value (typing.Any): a registered datatype id, a datatype, a python type, or
            any value to get the datatype of.

    Returns:
        str: datatype type id.
    """
    if isinstance(value, Datatype):
        return value.type_id
    if isinstance(value, str) and NYX_REGISTRY.get_datatype(value):
        return value
    if isinstance(value, type):
        for datatype in NYX_REGISTRY.iter_datatypes():
            if datatype.python_type is value:
                return datatype.type_id
        return OBJECT_DATATYPE.type_id
    return NYX_REGISTRY.infer_datatype(value).type_id


CORE_DATATYPES: tuple[Datatype, ...] = (
    OBJECT_DATATYPE,
    Datatype(
        type_id=CoreDatatypes.TYPE,
        display_name="Type",
        color="#B04BFF",
        caster=cast_to_type_id,
        default_factory=lambda: CoreDatatypes.OBJECT.value,
    ),
    Datatype(
        type_id=CoreDatatypes.BOOL,
        display_name="Boolean",
        color="#FF0000",
        caster=bool,
        python_type=bool,
        default_factory=bool,
    ),
    Datatype(
        type_id=CoreDatatypes.STRING,
        display_name="String",
        color="#FFA637",
        caster=str,
        python_type=str,
        default_factory=str,
        compatible_with=frozenset({CoreDatatypes.REFERENCE}),
    ),
    Datatype(
        type_id=CoreDatatypes.INT,
        display_name="Integer",
        color="#38D6A4",
        caster=int,
        python_type=int,
        default_factory=int,
    ),
    Datatype(
        type_id=CoreDatatypes.FLOAT,
        display_name="Float",
        color="#9BE04B",
        caster=float,
        python_type=float,
        default_factory=float,
    ),
    Datatype(
        type_id=CoreDatatypes.PATH,
        display_name="Path",
        color="#4BB8FF",
        caster=pathlib.PurePosixPath,
        python_type=pathlib.PurePosixPath,
    ),
    Datatype(
        type_id=CoreDatatypes.FLOW,
        display_name="Flow",
        color="#FFFFFF",
        plug_shape=GraphicsPlugShape.PENTAGON,
        selectable=False,
    ),
    Datatype(
        type_id=CoreDatatypes.REFERENCE,
        display_name="Reference",
        color="#0096FF",
        plug_shape=GraphicsPlugShape.SQUARE,
        compatible_with=frozenset({CoreDatatypes.STRING}),
    ),
)
