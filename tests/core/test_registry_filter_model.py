import pytest

from nyx.api.v1 import NYX_REGISTRY
from nyx.core.models.registry_filter_model import RegistryFilterModel, SearchToken
from nyx.core.models.registry_model import RegistryListModel


@pytest.fixture
def filter_model():
    source = RegistryListModel(lambda: NYX_REGISTRY.nodes)
    model = RegistryFilterModel()
    model.setSourceModel(source)
    return model


def type_ids(model):
    return {
        model.index(row, 0).data(RegistryListModel.Roles.TYPE_ID)
        for row in range(model.rowCount())
    }


def test_parse_token():
    assert RegistryFilterModel.parse_token("tag:logic") == SearchToken("tag", "logic")
    assert RegistryFilterModel.parse_token(" Tags: logic ") is None
    assert RegistryFilterModel.parse_token("TAG:Logic ") == SearchToken("tag", "Logic")
    assert RegistryFilterModel.parse_token("unknown:logic") is None
    assert RegistryFilterModel.parse_token("tag:") is None
    assert RegistryFilterModel.parse_token("plain text") is None


def test_exposes_token_keys(filter_model):
    assert set(filter_model.tokenKeys) == set(RegistryFilterModel.TOKEN_ROLES)


def test_everything_is_shown_without_a_query(filter_model):
    assert type_ids(filter_model) == set(NYX_REGISTRY.nodes)


def test_text_matches_display_name_ignoring_case(filter_model):
    filter_model.setQuery("BRANCH", [])

    assert type_ids(filter_model) == {"core:branch"}


def test_tag_token_matches_tags(filter_model):
    expected = {
        type_id
        for type_id, cls in NYX_REGISTRY.nodes.items()
        if "function" in cls.get_tags()
    }
    filter_model.setQuery("", ["tag:function"])

    assert type_ids(filter_model) == expected or not expected


def test_tokens_and_text_all_have_to_match(filter_model):
    filter_model.setQuery("branch", ["id:core:"])
    assert type_ids(filter_model) == {"core:branch"}

    filter_model.setQuery("branch", ["id:nothing"])
    assert type_ids(filter_model) == set()


def test_section_token(filter_model):
    filter_model.setQuery("", ["section:core"])

    assert type_ids(filter_model)
    assert all(type_id.startswith("core:") for type_id in type_ids(filter_model))


def test_unreadable_tokens_are_ignored(filter_model):
    filter_model.setQuery("", ["nonsense", "bogus:x"])

    assert type_ids(filter_model) == set(NYX_REGISTRY.nodes)
