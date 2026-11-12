import pathlib
import typing

from nyx.api.v1 import (
    NYX_REGISTRY,
    CoreDatatypes,
    Datatype,
    GraphicsPlugShape,
    OBJECT_DATATYPE,
)


def cast_to_type(value: typing.Any) -> type:
    """Get the python type a value stands for.

    Args:
        value (typing.Any): a python type, a datatype, the id of a registered datatype,
            or any value to get the type of.

    Returns:
        type: the class. Datatypes without a python type (e.g. object) give `object`.
    """
    if isinstance(value, type):
        return value
    if isinstance(value, Datatype):
        return value.python_type or object
    if isinstance(value, str):
        datatype = NYX_REGISTRY.get_datatype(value)
        if datatype is not None:
            return datatype.python_type or object
    return type(value)


CORE_DATATYPES: tuple[Datatype, ...] = (
    OBJECT_DATATYPE,
    Datatype(
        type_id=CoreDatatypes.TYPE,
        display_name="Type",
        color="#B04BFF",
        caster=cast_to_type,
        python_type=type,
        default_factory=lambda: object,
        is_wildcard=True,
    ),
    Datatype(
        type_id=CoreDatatypes.BOOL,
        display_name="Boolean",
        color="#FF0000",
        caster=bool,
        python_type=bool,
        default_factory=bool,
        is_wildcard=True,
    ),
    Datatype(
        type_id=CoreDatatypes.STRING,
        display_name="String",
        color="#FFA637",
        caster=str,
        python_type=str,
        default_factory=str,
        is_wildcard=True,
    ),
    Datatype(
        type_id=CoreDatatypes.INT,
        display_name="Integer",
        color="#38D6A4",
        caster=int,
        python_type=int,
        default_factory=int,
        compatible_with=frozenset({CoreDatatypes.FLOAT}),
    ),
    Datatype(
        type_id=CoreDatatypes.FLOAT,
        display_name="Float",
        color="#9BE04B",
        caster=float,
        python_type=float,
        default_factory=float,
        compatible_with=frozenset({CoreDatatypes.INT}),
    ),
    Datatype(
        type_id=CoreDatatypes.PATH,
        display_name="Path",
        color="#4BB8FF",
        caster=pathlib.PurePosixPath,
        python_type=pathlib.PurePosixPath,
    ),
    Datatype(
        type_id=CoreDatatypes.LIST,
        display_name="List",
        color="#FF5FB0",
        caster=list,
        python_type=list,
        default_factory=list,
        plug_shape=GraphicsPlugShape.BARS,
    ),
    Datatype(
        type_id=CoreDatatypes.DICT,
        display_name="Dictionary",
        color="#FFD84B",
        caster=dict,
        python_type=dict,
        default_factory=dict,
        plug_shape=GraphicsPlugShape.DIAMOND,
    ),
    Datatype(
        type_id=CoreDatatypes.FLOW,
        display_name="Flow",
        color="#FFFFFF",
        plug_shape=GraphicsPlugShape.PENTAGON,
        ignores_wildcards=True,
        selectable=False,
    ),
    Datatype(
        type_id=CoreDatatypes.STAGE_OBJECT_PATH,
        display_name="Object Path",
        color="#0096FF",
        plug_shape=GraphicsPlugShape.SQUARE,
        compatible_with=frozenset({CoreDatatypes.STRING}),
    ),
)
