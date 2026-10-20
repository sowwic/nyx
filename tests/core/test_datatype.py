import pytest

from nyx.api.v1 import NYX_REGISTRY, CoreDatatypes, Datatype
from nyx.core.exceptions import DatatypeCastError


def get(type_id: CoreDatatypes) -> Datatype:
    return NYX_REGISTRY.get_datatype(type_id)


def test_core_datatypes_are_registered():
    registered = {datatype.type_id for datatype in NYX_REGISTRY.iter_datatypes()}
    assert registered == set(CoreDatatypes)


def test_unknown_datatype_is_none():
    assert NYX_REGISTRY.get_datatype("missing:type") is None


@pytest.mark.parametrize(
    "type_id, value, expected",
    [
        (CoreDatatypes.BOOL, 1, True),
        (CoreDatatypes.STRING, 12, "12"),
        (CoreDatatypes.INT, "7", 7),
        (CoreDatatypes.FLOAT, 2, 2.0),
        (CoreDatatypes.OBJECT, [1], [1]),
    ],
)
def test_cast(type_id, value, expected):
    assert get(type_id).cast(value) == expected


def test_failed_cast_raises_cast_error():
    with pytest.raises(DatatypeCastError):
        get(CoreDatatypes.INT).cast("abc")


def test_wildcards_accept_everything():
    for wildcard in (CoreDatatypes.OBJECT, CoreDatatypes.TYPE):
        for other in NYX_REGISTRY.iter_datatypes():
            assert get(wildcard).accepts(other)
            assert other.accepts(get(wildcard))


def test_concrete_datatypes_accept_only_themselves():
    assert get(CoreDatatypes.BOOL).accepts(get(CoreDatatypes.BOOL))
    assert not get(CoreDatatypes.BOOL).accepts(get(CoreDatatypes.STRING))
