import pathlib

from nyx.api.v1 import CoreDatatypes, Datatype, DatatypeColor

CORE_DATATYPES: tuple[Datatype, ...] = (
    Datatype(
        type_id=CoreDatatypes.OBJECT,
        display_name="Object",
        color="#0096FF",
        is_wildcard=True,
    ),
    Datatype(
        type_id=CoreDatatypes.TYPE,
        display_name="Type",
        color="#B04BFF",
        is_wildcard=True,
    ),
    Datatype(
        type_id=CoreDatatypes.BOOL,
        display_name="Boolean",
        color=DatatypeColor.BOOL,
        caster=bool,
    ),
    Datatype(
        type_id=CoreDatatypes.STRING,
        display_name="String",
        color=DatatypeColor.STRING,
        caster=str,
    ),
    Datatype(
        type_id=CoreDatatypes.INT,
        display_name="Integer",
        color="#38D6A4",
        caster=int,
    ),
    Datatype(
        type_id=CoreDatatypes.FLOAT,
        display_name="Float",
        color="#9BE04B",
        caster=float,
    ),
    Datatype(
        type_id=CoreDatatypes.PATH,
        display_name="Path",
        color="#4BB8FF",
        caster=pathlib.PurePosixPath,
    ),
)
