import pytest

from nyx.api.v1 import Stage, CoreNodes, commands


def make_node(stage, type_id=CoreNodes.EMPTY, name=None):
    command = commands.CreateNodeCommand(stage=stage, type_id=type_id, name=name)
    stage.push_command(command)
    return command.result_node


@pytest.fixture
def changed_nodes():
    """Collects the nodes the stage reports as changed."""

    class Collector:
        def __init__(self):
            self.nodes = []

        def connect(self, stage):
            stage.itemChanged.connect(lambda node: self.nodes.append(node))

    return Collector()


def test_node_has_no_subtitle_by_default():
    node = make_node(Stage())
    assert node.subtitle == ""


def test_subtitle_can_be_set_by_a_node():
    node = make_node(Stage())

    node.subtitle = "extra text"

    assert node.subtitle == "extra text"


def test_setting_none_clears_the_subtitle():
    node = make_node(Stage())
    node.subtitle = "text"

    node.subtitle = None

    assert node.subtitle == ""


def test_setting_the_subtitle_reports_the_node_as_changed(changed_nodes):
    stage = Stage()
    node = make_node(stage)
    changed_nodes.connect(stage)

    node.subtitle = "extra text"

    assert node in changed_nodes.nodes


def test_subtitle_is_not_serialized():
    node = make_node(Stage())
    node.subtitle = "extra text"

    assert "extra text" not in str(node.serialize())


def test_bound_subtitle_follows_the_display_value_of_a_component():
    stage = Stage()
    node = make_node(stage, CoreNodes.BRANCH)
    node.bind_subtitle_to_component("condition")

    node["condition"].push_value(False)

    assert node.subtitle == "False"


def test_bound_subtitle_uses_the_formatter():
    stage = Stage()
    node = make_node(stage, CoreNodes.BRANCH)
    node.bind_subtitle_to_component(
        "condition", lambda component: f"condition={component.cached_value}"
    )

    assert node.subtitle == "condition=True"


def test_binding_reports_the_node_as_changed_with_its_component(changed_nodes):
    stage = Stage()
    node = make_node(stage, CoreNodes.BRANCH)
    node.bind_subtitle_to_component("condition")
    changed_nodes.connect(stage)

    node["condition"].push_value(False)

    assert node in changed_nodes.nodes


def test_binding_ignores_other_components(changed_nodes):
    stage = Stage()
    node = make_node(stage, CoreNodes.BRANCH)
    node.bind_subtitle_to_component("condition")
    changed_nodes.connect(stage)

    node["flow"].is_active = False

    assert node not in changed_nodes.nodes


def test_setting_a_text_ends_the_binding():
    stage = Stage()
    node = make_node(stage, CoreNodes.BRANCH)
    node.bind_subtitle_to_component("condition")

    node.subtitle = "fixed"
    node["condition"].push_value(False)

    assert node.subtitle == "fixed"


def test_binding_to_a_missing_component_gives_no_subtitle():
    node = make_node(Stage())
    node.bind_subtitle_to_component("missing")

    assert node.subtitle == ""


# ======== Getter and setter ========= #


@pytest.mark.parametrize("type_id", [CoreNodes.GET, CoreNodes.SET])
def test_getter_and_setter_show_the_component_they_point_at(type_id):
    stage = Stage()
    target = make_node(stage, CoreNodes.LOG, name="target")
    node = make_node(stage, type_id)
    assert node.subtitle == ""

    node["component"].push_value(f"{target.path.as_posix()}.message")

    assert node.subtitle == f"{target.path.as_posix()}.message"


@pytest.mark.parametrize("type_id", [CoreNodes.GET, CoreNodes.SET])
def test_subtitle_reports_the_node_when_the_path_changes(type_id, changed_nodes):
    stage = Stage()
    target = make_node(stage, CoreNodes.LOG, name="target")
    node = make_node(stage, type_id)
    changed_nodes.connect(stage)

    node["component"].push_value(f"{target.path.as_posix()}.level")

    assert node in changed_nodes.nodes


def test_subtitle_follows_a_rename_of_the_target():
    stage = Stage()
    target = make_node(stage, CoreNodes.LOG, name="target")
    node = make_node(stage, CoreNodes.GET)
    node["component"].push_value(f"{target.path.as_posix()}.message")

    stage.push_command(
        commands.RenameNodeCommand(stage=stage, node=target, new_name="renamed")
    )

    assert node.subtitle == "/stage/renamed.message"


def test_relative_path_is_shown_as_the_path_of_the_target():
    stage = Stage()
    make_node(stage, CoreNodes.LOG, name="target")
    node = make_node(stage, CoreNodes.SET)

    node["component"].push_value("./target.message")

    assert node.subtitle == "/stage/target.message"


def test_unresolved_path_is_shown_as_typed():
    node = make_node(Stage(), CoreNodes.GET)

    node["component"].push_value("/stage/nowhere.value")

    assert node.subtitle == "/stage/nowhere.value"
