import pytest

from nyx.api.v1 import (
    Stage,
    NodeComponent,
    NodeDeserializationContext,
    commands,
    exceptions,
    CoreNodes,
    CoreNodeComponents,
    CoreDatatypes,
)


def make_branch(stage: Stage):
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.BRANCH)
    stage.push_command(command)
    return command.result_node


@pytest.fixture
def value():
    component = make_branch(Stage())["condition"]
    component.set_datatype(CoreDatatypes.OBJECT)
    return component


def test_default_datatype_is_object(value):
    assert value.datatype_id == CoreDatatypes.OBJECT
    assert value.datatype.is_wildcard


def test_object_evaluates_without_casting(value):
    value.push_value("[1, 2]")
    assert value.cached_value == [1, 2]
    assert value.is_valid


def test_typed_value_is_cast_after_evaluation(value):
    value.set_datatype(CoreDatatypes.INT)
    value.push_value("3.0")
    assert value.cached_value == 3
    assert value.display_value == "3"


def test_setting_datatype_recasts_current_value(value):
    value.push_value("5")
    value.set_datatype(CoreDatatypes.STRING)
    assert value.cached_value == "5"


def test_failed_cast_keeps_previous_value_and_marks_invalid(value):
    value.set_datatype(CoreDatatypes.INT)
    value.push_value("4")
    value.push_value("abc")
    assert value.cached_value == 4
    assert value.raw_value == "abc"
    assert not value.is_valid
    assert value.value_storage.cast_error


def test_next_valid_value_clears_invalid_state(value):
    value.set_datatype(CoreDatatypes.INT)
    value.push_value("abc")
    value.push_value("2")
    assert value.is_valid
    assert value.cached_value == 2


def test_none_becomes_the_default_of_the_datatype(value):
    value.set_datatype(CoreDatatypes.INT)
    value.push_value(None)
    assert value.cached_value == 0
    assert value.is_valid


def test_none_stays_none_for_datatypes_without_a_default(value):
    value.push_value(None)
    assert value.cached_value is None


def test_setting_a_datatype_on_an_empty_value_pushes_its_default():
    component = make_branch(Stage())["condition"]
    component.push_value(None)

    component.set_datatype(CoreDatatypes.STRING)

    assert component.raw_value == ""
    assert component.cached_value == ""


def test_setting_a_datatype_keeps_an_existing_value():
    component = make_branch(Stage())["condition"]
    component.push_value("5")

    component.set_datatype(CoreDatatypes.INT)

    assert component.raw_value == "5"
    assert component.cached_value == 5


def test_reset_to_type_default_uses_the_datatype_default():
    component = make_branch(Stage())["condition"]
    component.set_datatype(CoreDatatypes.INT)
    component.push_value(9)

    component.reset_value_to_type_default()

    assert component.cached_value == 0


def test_unknown_datatype_falls_back_to_object_but_is_kept(value):
    value.set_datatype("missing:type")
    assert value.datatype.is_wildcard
    assert value.datatype_id == "missing:type"
    assert value.serialize()["datatype"] == "missing:type"


def test_datatype_survives_serialization(value):
    value.set_datatype(CoreDatatypes.FLOAT)
    value.push_value("1")
    node = value.node
    data = value.serialize()
    context = NodeDeserializationContext(stage=node.stage, entry_node=node)

    restored = NodeComponent.deserialize(data=data, node=node, context=context)

    assert restored.datatype_id == CoreDatatypes.FLOAT
    assert restored.cached_value == 1.0


def test_legacy_data_without_datatype_deserializes(value):
    data = value.serialize()
    del data["datatype"]
    node = value.node
    context = NodeDeserializationContext(stage=node.stage, entry_node=node)

    restored = NodeComponent.deserialize(data=data, node=node, context=context)

    assert restored.datatype_id == CoreDatatypes.OBJECT


def test_linking_incompatible_datatypes_is_rejected():
    stage = Stage()
    source = make_branch(stage)["condition"]
    target = make_branch(stage)["condition"]
    source.readable = True
    source.set_datatype(CoreDatatypes.STRING)
    target.set_datatype(CoreDatatypes.BOOL)

    with pytest.raises(exceptions.NodeComponentLinkError, match="Incompatible"):
        stage.link_components(source, target)


def test_linking_wildcard_to_concrete_datatype_is_allowed():
    stage = Stage()
    source = make_branch(stage)["condition"]
    target = make_branch(stage)["condition"]
    source.readable = True
    source.set_datatype(CoreDatatypes.OBJECT)
    target.set_datatype(CoreDatatypes.BOOL)

    assert stage.link_components(source, target) is not None


def test_flow_and_comment_have_their_own_datatypes():
    stage = Stage()
    command = commands.CreateNodeCommand(stage=stage, type_id=CoreNodes.ACTION)
    stage.push_command(command)
    node = command.result_node
    add = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.COMMENT, name="note"
    )
    stage.push_command(add)

    assert node["flow"].datatype_id == CoreDatatypes.FLOW
    assert add.result_component.datatype_id == CoreDatatypes.STRING


class BadDefaultComponent(NodeComponent):
    @classmethod
    def get_type_id(cls) -> str:
        return "test:bad_default"

    @classmethod
    def get_type_default_datatype(cls) -> str:
        return CoreDatatypes.INT

    @classmethod
    def get_type_default_value(cls):
        return "not a number"


class GoodDefaultComponent(BadDefaultComponent):
    @classmethod
    def get_type_default_value(cls):
        return 7


def test_invalid_type_default_falls_back_to_the_datatype_default(caplog):
    with caplog.at_level("WARNING"):
        component = BadDefaultComponent()

    assert component.cached_value == 0
    assert component.is_valid
    assert "not valid for datatype Integer" in caplog.text


def test_valid_type_default_is_used(caplog):
    with caplog.at_level("WARNING"):
        component = GoodDefaultComponent()

    assert component.cached_value == 7
    assert "not valid for datatype" not in caplog.text


def test_plug_shape_follows_the_datatype(value):
    from nyx.api.v1 import GraphicsPlugShape

    assert value.get_plug_shape() is GraphicsPlugShape.SQUARE_MATRIX
    value.set_datatype(CoreDatatypes.FLOW)
    assert value.get_plug_shape() is GraphicsPlugShape.PENTAGON
