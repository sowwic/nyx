from nyx.core.layered_config import NyxConfig, get_app_config
from nyx.editor.utils.common import are_hover_diagnostics_enabled


def test_app_config_is_the_config_of_the_application(qapp):
    assert get_app_config() is qapp.config


def test_without_an_application_config_a_resolved_one_is_made(monkeypatch):
    resolved = []
    monkeypatch.setattr(NyxConfig, "resolve", lambda self: resolved.append(self))
    monkeypatch.setattr(
        "nyx.core.layered_config.QtCore.QCoreApplication.instance", lambda: None
    )

    config = get_app_config()

    assert isinstance(config, NyxConfig)
    assert resolved == [config]


def test_hover_diagnostics_follow_the_application_config(qapp, monkeypatch):
    node_config = qapp.config.values.editor_widgets.graphics_stage.nodes
    monkeypatch.setattr("nyx.editor.utils.common.DEBUG", 0)
    saved = node_config.hover_diagnostics
    try:
        node_config.hover_diagnostics = True
        assert are_hover_diagnostics_enabled()

        node_config.hover_diagnostics = False
        assert not are_hover_diagnostics_enabled()
    finally:
        node_config.hover_diagnostics = saved
