import logging

from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues

from nyx.core.config_values.bridge_values import NyxBridgeConfigValues
from nyx.core.config_values.editor_values import (
    NyxEditorBehaviourConfigValues,
    NyxEditorSessionConfigValues,
)
from nyx.core.config_values.main_window_values import NyxMainWindowConfigValues
from nyx.core.config_values.style_values import NyxEditorStyleConfigValues
from nyx.core.config_values.widgets_values import NyxEditorWidgetsConfigValues


class NyxConfigValues(NyxBaseConfigValues):
    """Main container for config values."""

    main_window: NyxMainWindowConfigValues = Field(
        default_factory=NyxMainWindowConfigValues, alias="main_window"
    )
    """Main window settings."""

    bridge: NyxBridgeConfigValues = Field(
        default_factory=NyxBridgeConfigValues, alias="bridge"
    )
    """Server external processes connect to."""
    editor_behaviour: NyxEditorBehaviourConfigValues = Field(
        default_factory=NyxEditorBehaviourConfigValues, alias="editor_behaviour"
    )
    """Editor behaviour settings."""
    editor_session: NyxEditorSessionConfigValues = Field(
        default_factory=NyxEditorSessionConfigValues, alias="editor_session"
    )
    """Editor session state."""
    editor_style: NyxEditorStyleConfigValues = Field(
        default_factory=NyxEditorStyleConfigValues, alias="editor_style"
    )
    """Editor styling settings."""
    editor_widgets: NyxEditorWidgetsConfigValues = Field(
        default_factory=NyxEditorWidgetsConfigValues, alias="editor_widgets"
    )
    """Settings of the editor widgets."""
    logging_level: int = Field(default=logging.INFO)
    """Logging level of the application."""
    plugin_paths: list[str] = Field(default_factory=list)
    """Additional directories to discover plugins in."""
