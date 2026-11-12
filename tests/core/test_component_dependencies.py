import pytest

from nyx.api.v1 import CoreNodeComponents, CoreNodes, Stage, commands


def create(stage, type_id=CoreNodes.ACTION, name=None):
    command = commands.CreateNodeCommand(stage=stage, type_id=type_id, name=name)
    stage.push_command(command)
    return command.result_node


def add_value(stage, node, name):
    command = commands.AddNodeComponentCommand(
        node=node, type_id=CoreNodeComponents.VALUE, name=name
    )
    stage.push_command(command)
    return command.result_component


class Recorder:
    """Records the roles reported as changed for a component."""

    def __init__(self, component):
        self.component = component
        self.reports = []
        component.model().dataChanged.connect(self._on_changed)

    def _on_changed(self, top_left, bottom_right, roles):
        if top_left.row() <= self.component.row() <= bottom_right.row():
            self.reports.append(set(roles))

    def reported(self, role):
        return any(role in roles for roles in self.reports)

    def clear(self):
        self.reports.clear()


@pytest.fixture
def two_values():
    stage = Stage()
    node = create(stage)
    return stage, node, add_value(stage, node, "source"), add_value(stage, node, "other")


def test_dependent_is_reported_changed_with_its_source(two_values):
    _stage, node, source, dependent = two_values
    roles = source.Roles
    node.components_model.add_dependency(dependent, on=source)
    recorder = Recorder(dependent)

    source.push_value("changed")

    assert recorder.reported(roles.DISPLAY_VALUE)
    assert recorder.reported(roles.CACHED_VALUE)
    assert recorder.reported(roles.IS_VALID)


def test_without_a_dependency_nothing_else_is_reported(two_values):
    _stage, _node, source, dependent = two_values
    recorder = Recorder(dependent)
    source.push_value("changed")
    assert recorder.reports == []


def test_dependent_answers_with_the_state_the_source_has_now(two_values):
    _stage, node, source, dependent = two_values
    node.components_model.add_dependency(dependent, on=source)
    dependent.get_display_value = lambda: f"seen:{source.cached_value}"
    index = dependent.index()
    answers = []
    node.components_model.dataChanged.connect(
        lambda top_left, _b, roles: answers.append(
            index.data(source.Roles.DISPLAY_VALUE)
        )
        if top_left.row() == dependent.row()
        else None
    )

    source.push_value("new")
    assert answers and answers[-1] == "seen:new"


def test_only_the_wanted_roles_of_the_source_trigger_the_refresh(two_values):
    _stage, node, source, dependent = two_values
    node.components_model.add_dependency(
        dependent, on=source, when=[source.Roles.RAW_VALUE]
    )
    recorder = Recorder(dependent)

    source.is_expanded = not source.is_expanded  # unrelated to the value
    assert recorder.reports == []
    source.push_value("changed")
    assert recorder.reports


def test_default_does_not_react_to_unrelated_roles(two_values):
    _stage, node, source, dependent = two_values
    node.components_model.add_dependency(dependent, on=source)
    recorder = Recorder(dependent)

    source.is_expanded = not source.is_expanded
    assert recorder.reports == []


def test_the_refreshed_roles_can_be_chosen(two_values):
    _stage, node, source, dependent = two_values
    node.components_model.add_dependency(
        dependent, on=source, refresh=[source.Roles.DISPLAY_VALUE]
    )
    recorder = Recorder(dependent)

    source.push_value("changed")
    assert recorder.reported(source.Roles.DISPLAY_VALUE)
    assert not recorder.reported(source.Roles.CACHED_VALUE)


def test_dependencies_chain(two_values):
    stage, node, source, middle = two_values
    last = add_value(stage, node, "last")
    node.components_model.add_dependency(middle, on=source)
    node.components_model.add_dependency(last, on=middle)
    recorder = Recorder(last)

    source.push_value("changed")
    assert recorder.reports


def test_cycles_stop_instead_of_looping(two_values):
    _stage, node, first, second = two_values
    node.components_model.add_dependency(second, on=first)
    node.components_model.add_dependency(first, on=second)
    recorder_first, recorder_second = Recorder(first), Recorder(second)

    first.push_value("changed")  # would never return if the cycle was followed
    assert recorder_second.reports
    assert recorder_first.reports


def test_removed_component_is_no_longer_refreshed(two_values):
    stage, node, source, dependent = two_values
    node.components_model.add_dependency(dependent, on=source)
    node.components_model.remove_component(dependent.uuid)
    assert node.components_model._dependencies == []

    source.push_value("changed")  # nothing to refresh, and no error


def test_removed_source_drops_its_dependencies(two_values):
    _stage, node, source, dependent = two_values
    node.components_model.add_dependency(dependent, on=source)
    node.components_model.remove_dependencies(source)
    recorder = Recorder(dependent)

    source.push_value("changed")
    assert recorder.reports == []


# ======== Getter ========= #


def test_getter_value_is_refreshed_when_the_component_path_changes():
    stage = Stage()
    target = create(stage, CoreNodes.LOG, name="target")
    target["message"].push_value("hello")
    getter = create(stage, CoreNodes.GET, name="getter")
    value = getter["value"]
    recorder = Recorder(value)

    getter["component"].push_value("/stage/target.message")

    assert recorder.reported(value.Roles.DISPLAY_VALUE)
    assert value.index().data(value.Roles.DISPLAY_VALUE) == "hello"


def test_getter_value_follows_the_path_through_edits_and_undo():
    stage = Stage()
    first = create(stage, CoreNodes.LOG, name="first")
    second = create(stage, CoreNodes.LOG, name="second")
    first["message"].push_value("one")
    second["message"].push_value("two")
    getter = create(stage, CoreNodes.GET, name="getter")
    value = getter["value"]
    getter["component"].push_value("/stage/first.message")
    index = value.index()
    display = lambda: index.data(value.Roles.DISPLAY_VALUE)  # noqa: E731
    assert display() == "one"

    stage.push_command(
        commands.SetNodeComponentValueCommand(
            stage=stage,
            node_component=getter["component"],
            value="/stage/second.message",
            raw=True,
        )
    )
    assert display() == "two"
    stage.undo_stack.undo()
    assert display() == "one"
