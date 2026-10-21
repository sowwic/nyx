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
    wildcard = CoreDatatypes.OBJECT
    for other in NYX_REGISTRY.iter_datatypes():
        assert get(wildcard).accepts(other)
        assert other.accepts(get(wildcard))


def test_type_is_a_concrete_datatype():
    type_datatype = get(CoreDatatypes.TYPE)
    assert not type_datatype.is_wildcard
    assert type_datatype.accepts(type_datatype)
    assert type_datatype.accepts(get(CoreDatatypes.OBJECT))
    assert not type_datatype.accepts(get(CoreDatatypes.INT))
    assert not get(CoreDatatypes.INT).accepts(type_datatype)


def test_concrete_datatypes_accept_only_themselves():
    assert get(CoreDatatypes.INT).accepts(get(CoreDatatypes.INT))
    assert not get(CoreDatatypes.INT).accepts(get(CoreDatatypes.PATH))


def test_bool_is_a_wildcard():
    boolean = get(CoreDatatypes.BOOL)
    assert boolean.is_wildcard
    assert boolean.accepts(get(CoreDatatypes.PATH))
    assert boolean.cast([]) is False
    assert boolean.cast("text") is True


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, CoreDatatypes.BOOL),
        (1, CoreDatatypes.INT),
        (1.5, CoreDatatypes.FLOAT),
        ("text", CoreDatatypes.STRING),
        ([1], CoreDatatypes.OBJECT),
    ],
)
def test_infer_datatype_uses_the_exact_python_type(value, expected):
    assert NYX_REGISTRY.infer_datatype(value).type_id == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (CoreDatatypes.BOOL, CoreDatatypes.BOOL),  # a registered datatype id
        (float, CoreDatatypes.FLOAT),  # a python type
        (3, CoreDatatypes.INT),  # any other value gives its own type
        (dict, CoreDatatypes.OBJECT),
    ],
)
def test_type_datatype_gets_the_type_from_any_input(value, expected):
    assert get(CoreDatatypes.TYPE).cast(value) == expected


def test_type_datatype_accepts_a_datatype():
    assert get(CoreDatatypes.TYPE).cast(get(CoreDatatypes.INT)) == CoreDatatypes.INT


@pytest.mark.parametrize(
    "type_id, expected",
    [
        (CoreDatatypes.BOOL, False),
        (CoreDatatypes.STRING, ""),
        (CoreDatatypes.INT, 0),
        (CoreDatatypes.FLOAT, 0.0),
        (CoreDatatypes.TYPE, "core:object"),
        (CoreDatatypes.OBJECT, None),
        (CoreDatatypes.PATH, None),
        (CoreDatatypes.FLOW, None),
    ],
)
def test_default_values(type_id, expected):
    default = get(type_id).create_default()
    assert default == expected
    assert type(default) is type(expected)


def test_plug_shape_defaults_to_circle():
    from nyx.api.v1 import GraphicsPlugShape

    assert Datatype(type_id="t:t", display_name="T", color="#000").plug_shape is (
        GraphicsPlugShape.CIRCLE
    )
    assert get(CoreDatatypes.BOOL).plug_shape is GraphicsPlugShape.CIRCLE
    assert get(CoreDatatypes.FLOW).plug_shape is GraphicsPlugShape.PENTAGON


def test_reference_is_a_square_that_exchanges_paths_with_strings():
    from nyx.api.v1 import GraphicsPlugShape

    reference = get(CoreDatatypes.REFERENCE)
    assert reference.plug_shape is GraphicsPlugShape.SQUARE
    assert reference.accepts(get(CoreDatatypes.STRING))
    assert get(CoreDatatypes.STRING).accepts(reference)
    assert not reference.accepts(get(CoreDatatypes.INT))


def test_only_flow_is_not_selectable():
    not_selectable = {
        datatype.type_id
        for datatype in NYX_REGISTRY.iter_datatypes()
        if not datatype.selectable
    }
    assert not_selectable == {CoreDatatypes.FLOW}
