import pytest

from nyx.core.models.stage_filter_model import StageFilterModel
from nyx.api.v1 import CoreNodes, Node, Stage
from stage_helpers import create_node


@pytest.fixture
def stage():
    return Stage()


@pytest.fixture
def filter_model(stage):
    model = StageFilterModel()
    model.setSourceModel(stage)
    return model


def visible_names(filter_model, stage):
    """Names of the nodes under the root node that the filter keeps."""
    root = filter_model.mapFromSource(stage.root_node.index())
    return [
        filter_model.index(row, 0, root).data(Node.Roles.NAME)
        for row in range(filter_model.rowCount(root))
    ]


def test_every_node_stays_without_text(stage, filter_model):
    create_node(stage, name="alpha")
    create_node(stage, name="beta")

    assert visible_names(filter_model, stage) == ["alpha", "beta"]


def test_only_nodes_with_the_text_in_their_name_stay(stage, filter_model):
    create_node(stage, name="alpha")
    create_node(stage, name="beta")

    filter_model.setQuery("alp", [])

    assert visible_names(filter_model, stage) == ["alpha"]


def test_text_is_compared_ignoring_case_and_surrounding_spaces(stage, filter_model):
    create_node(stage, name="Alpha")

    filter_model.setQuery("  aLPH ", [])

    assert visible_names(filter_model, stage) == ["Alpha"]


def test_the_parents_of_a_match_stay_but_not_their_other_children(stage, filter_model):
    parent = create_node(stage, name="parent")
    create_node(stage, name="needle", parent=parent)
    create_node(stage, name="other", parent=parent)
    create_node(stage, name="unrelated")

    filter_model.setQuery("needle", [])

    assert visible_names(filter_model, stage) == ["parent"]
    parent_index = filter_model.mapFromSource(parent.index())
    assert filter_model.rowCount(parent_index) == 1
    assert filter_model.index(0, 0, parent_index).data(Node.Roles.NAME) == "needle"


def test_the_root_node_stays_when_nothing_matches(stage, filter_model):
    create_node(stage, name="alpha")

    filter_model.setQuery("zzz", [])

    assert filter_model.mapFromSource(stage.root_node.index()).isValid()
    assert visible_names(filter_model, stage) == []


def test_clearing_the_text_brings_every_node_back(stage, filter_model):
    create_node(stage, name="alpha")
    create_node(stage, name="beta")
    filter_model.setQuery("alp", [])

    filter_model.setQuery("", [])

    assert visible_names(filter_model, stage) == ["alpha", "beta"]


def test_the_name_shown_counts_as_well_as_the_address_name(stage, filter_model):
    node = create_node(stage, name="alpha")
    node.set_display_name("Shiny Thing")

    filter_model.setQuery("shiny", [])

    assert visible_names(filter_model, stage) == ["alpha"]
    filter_model.setQuery("alph", [])
    assert visible_names(filter_model, stage) == ["alpha"]


def test_renamed_node_follows_the_filter(stage, filter_model):
    node = create_node(stage, name="alpha")
    filter_model.setQuery("beta", [])
    assert visible_names(filter_model, stage) == []

    node.set_display_name("beta_node")

    assert visible_names(filter_model, stage) == ["alpha"]


def test_tag_token_keeps_the_nodes_with_a_tag_containing_the_value(stage, filter_model):
    create_node(stage, name="plain")
    create_node(stage, CoreNodes.FOR_LOOP, name="loop")

    filter_model.setQuery("", ["tag:log"])

    assert visible_names(filter_model, stage) == ["loop"]


def test_type_and_id_tokens_look_at_the_type_of_the_node(stage, filter_model):
    create_node(stage, name="plain")
    create_node(stage, CoreNodes.LOG, name="logger")

    filter_model.setQuery("", [f"id:{CoreNodes.LOG}"])
    assert visible_names(filter_model, stage) == ["logger"]

    filter_model.setQuery("", ["type:log"])
    assert visible_names(filter_model, stage) == ["logger"]


def test_text_and_tokens_have_to_match_together(stage, filter_model):
    create_node(stage, CoreNodes.FOR_LOOP, name="first")
    create_node(stage, CoreNodes.FOR_LOOP, name="second")
    create_node(stage, name="third")

    filter_model.setQuery("sec", ["tag:logic"])

    assert visible_names(filter_model, stage) == ["second"]


def test_a_match_keeps_its_parents_when_searching_by_token(stage, filter_model):
    parent = create_node(stage, name="parent")
    create_node(stage, CoreNodes.FOR_LOOP, name="loop", parent=parent)
    create_node(stage, name="plain", parent=parent)

    filter_model.setQuery("", ["tag:logic"])

    assert visible_names(filter_model, stage) == ["parent"]
    assert filter_model.rowCount(filter_model.mapFromSource(parent.index())) == 1


def test_unknown_token_keys_are_ignored(stage, filter_model):
    create_node(stage, name="alpha")

    filter_model.setQuery("", ["nope:x"])

    assert not filter_model.is_active
    assert visible_names(filter_model, stage) == ["alpha"]


def test_token_keys_are_what_the_search_bar_can_make_tokens_of(filter_model):
    assert set(filter_model.tokenKeys) == {"type", "id", "tag", "path"}


def test_path_token_keeps_the_nodes_with_the_value_in_their_path(stage, filter_model):
    parent = create_node(stage, name="parent")
    create_node(stage, name="child", parent=parent)
    create_node(stage, name="other")

    filter_model.setQuery("", ["path:parent/child"])

    assert visible_names(filter_model, stage) == ["parent"]
    assert filter_model.rowCount(filter_model.mapFromSource(parent.index())) == 1


def test_path_token_matches_every_node_below_a_path_prefix(stage, filter_model):
    parent = create_node(stage, name="parent")
    create_node(stage, name="one", parent=parent)
    create_node(stage, name="two", parent=parent)
    create_node(stage, name="other")

    filter_model.setQuery("", [f"path:{parent.path.as_posix()}/"])

    assert filter_model.rowCount(filter_model.mapFromSource(parent.index())) == 2
    assert visible_names(filter_model, stage) == ["parent"]
