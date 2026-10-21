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
        if other.ignores_wildcards:
            continue
        assert get(wildcard).accepts(other)
        assert other.accepts(get(wildcard))


def test_flow_ignores_wildcards():
    flow = get(CoreDatatypes.FLOW)

    assert flow.ignores_wildcards
    assert flow.accepts(flow)
    for other in NYX_REGISTRY.iter_datatypes():
        if other.type_id == CoreDatatypes.FLOW:
            continue
        assert not flow.accepts(other)
        assert not other.accepts(flow)


def test_datatype_can_still_list_compatible_types_when_ignoring_wildcards():
    from nyx.core.datatypes.datatype import Datatype

    special = Datatype(
        type_id="t:special",
        display_name="Special",
        color="#000000",
        ignores_wildcards=True,
        compatible_with=frozenset({CoreDatatypes.INT}),
    )

    assert special.accepts(get(CoreDatatypes.INT))
    assert not special.accepts(get(CoreDatatypes.OBJECT))


def test_type_datatype_is_for_classes():
    type_datatype = get(CoreDatatypes.TYPE)
    assert type_datatype.python_type is type
    assert NYX_REGISTRY.infer_datatype(int) is type_datatype
    assert type_datatype.accepts(type_datatype)
    assert type_datatype.accepts(get(CoreDatatypes.OBJECT))


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
        ([1], CoreDatatypes.LIST),
        ({"a": 1}, CoreDatatypes.DICT),
        ({1}, CoreDatatypes.OBJECT),
    ],
)
def test_infer_datatype_uses_the_exact_python_type(value, expected):
    assert NYX_REGISTRY.infer_datatype(value).type_id == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (CoreDatatypes.BOOL, bool),  # a registered datatype id
        (CoreDatatypes.OBJECT, object),  # a datatype without a python type
        (float, float),  # a class stays as it is
        (dict, dict),
        (3, int),  # any other value gives its own type
        ("text", str),
    ],
)
def test_type_datatype_gets_the_class_from_any_input(value, expected):
    assert get(CoreDatatypes.TYPE).cast(value) == expected


def test_type_datatype_accepts_a_datatype():
    assert get(CoreDatatypes.TYPE).cast(get(CoreDatatypes.INT)) is int


@pytest.mark.parametrize(
    "type_id, expected",
    [
        (CoreDatatypes.BOOL, False),
        (CoreDatatypes.STRING, ""),
        (CoreDatatypes.INT, 0),
        (CoreDatatypes.FLOAT, 0.0),
        (CoreDatatypes.TYPE, object),
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


# ======== List and dictionary ========= #


@pytest.mark.parametrize(
    "type_id, value, expected",
    [
        (CoreDatatypes.LIST, [1, 2], [1, 2]),
        (CoreDatatypes.LIST, (1, 2), [1, 2]),
        (CoreDatatypes.LIST, range(3), [0, 1, 2]),
        (CoreDatatypes.DICT, {"a": 1}, {"a": 1}),
        (CoreDatatypes.DICT, [("a", 1), ("b", 2)], {"a": 1, "b": 2}),
    ],
)
def test_list_and_dict_casts(type_id, value, expected):
    result = get(type_id).cast(value)

    assert result == expected
    assert type(result) is type(expected)


@pytest.mark.parametrize(
    "type_id, value", [(CoreDatatypes.LIST, 5), (CoreDatatypes.DICT, 5)]
)
def test_list_and_dict_reject_values_that_are_not_collections(type_id, value):
    with pytest.raises(DatatypeCastError):
        get(type_id).cast(value)


@pytest.mark.parametrize("type_id", [CoreDatatypes.LIST, CoreDatatypes.DICT])
def test_list_and_dict_defaults_are_new_empty_collections(type_id):
    first = get(type_id).create_default()
    second = get(type_id).create_default()

    assert first == second == get(type_id).python_type()
    assert first is not second


def test_list_and_dict_are_concrete_with_own_plug_shapes():
    from nyx.api.v1 import GraphicsPlugShape

    list_type, dict_type = get(CoreDatatypes.LIST), get(CoreDatatypes.DICT)

    assert not list_type.is_wildcard and not dict_type.is_wildcard
    assert list_type.plug_shape is GraphicsPlugShape.BARS
    assert dict_type.plug_shape is GraphicsPlugShape.DIAMOND
    assert list_type.accepts(list_type) and dict_type.accepts(dict_type)
    assert list_type.accepts(get(CoreDatatypes.OBJECT))
    assert dict_type.accepts(get(CoreDatatypes.OBJECT))
    assert not list_type.accepts(dict_type)
    assert not dict_type.accepts(list_type)
    assert not list_type.accepts(get(CoreDatatypes.INT))
    assert not get(CoreDatatypes.INT).accepts(dict_type)
