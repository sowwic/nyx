import pytest
from json_config.api import ConfigValues

from nyx.core.config_values import NyxBaseConfigValues, NyxConfigValues
from nyx.static.enums import LinkAnimationStyle


def iter_fields(values_class=NyxConfigValues, path=""):
    """Yield (path, field info) of every field in the tree of config values."""
    for name, field in values_class.model_fields.items():
        yield f"{path}{name}", field
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, ConfigValues):
            yield from iter_fields(annotation, f"{path}{name}.")


def test_every_config_value_has_a_description():
    missing = [path for path, field in iter_fields() if not field.description]

    assert missing == []


def test_the_walk_reaches_nested_values():
    paths = {path for path, _field in iter_fields()}

    assert "editor_style.animations.link_glow.layers" in paths
    assert "editor_widgets.graphics_stage.highlight_flow_chain_style" in paths
    assert "main_window.layout.state" in paths


def test_descriptions_do_not_change_the_values():
    assert NyxConfigValues().to_dict()["editor_session"]["max_recent_files"] == 10


@pytest.mark.parametrize("style", list(LinkAnimationStyle))
def test_style_description_lists_every_style(style):
    stage = NyxConfigValues().editor_widgets.graphics_stage
    field = type(stage).model_fields["highlight_flow_chain_style"]

    assert style.value in field.description


def iter_values_classes(values_class=NyxConfigValues):
    """Yield every config values class in the tree."""
    yield values_class
    for field in values_class.model_fields.values():
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, ConfigValues):
            yield from iter_values_classes(annotation)


def test_every_config_values_class_reads_attribute_docstrings():
    classes = list(iter_values_classes())

    assert len(classes) > 5
    for values_class in classes:
        assert issubclass(values_class, NyxBaseConfigValues), values_class
        assert values_class.model_config["use_attribute_docstrings"], values_class


def test_description_is_the_docstring_of_the_field():
    from nyx.core.config_values.editor_values import NyxEditorSessionConfigValues

    field = NyxEditorSessionConfigValues.model_fields["max_recent_files"]

    assert field.description == "Number of recent files that are kept."
