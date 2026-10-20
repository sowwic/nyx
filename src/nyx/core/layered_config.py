import pathlib
import logging

from pydantic.dataclasses import Field
from json_config.api import ConfigLayer, ConfigValues, LayeredConfig

from ..static.paths import USER_CONFIG_FILE_PATH

MAX_RECENT_FILES = 10


class NyxMainWindowLayoutConfigValues(ConfigValues):
    """Main window dock layout config values.

    Attributes:
        version: layout version the state was saved with
        state: base64 encoded Qt window state
    """

    version: int = Field(default=0)
    state: str | None = Field(default=None)


class NyxMainWindowConfigValues(ConfigValues):
    """Main window config values.

    Attributes:
        size: window size
        position: window position
        is_always_on_top: window stays on top
    """

    size: tuple[int, int] | None = Field(default=None)
    position: tuple[int, int] | None = Field(default=None)
    is_always_on_top: bool = Field(default=False)
    layout: NyxMainWindowLayoutConfigValues = Field(
        default_factory=NyxMainWindowLayoutConfigValues, alias="layout"
    )


class NyxEditorStyleConfigValues(ConfigValues):
    """Editor styling config values.

    Attributes:
        dark_mode: dark mode enabled
    """

    dark_mode: bool = Field(default=True)


class NyxEditorLogWidgetConfigValues(ConfigValues):
    """Logger widget config values.

    Attributes:
        auto_scroll: view scroll on new items added
    """

    auto_scroll: bool = Field(default=True)
    expanded_height: int = Field(default=220)
    is_expanded: bool = Field(default=False)


class NyxEditorGraphicsNodeConfigValues(ConfigValues):
    """Graphics node config values.

    Attributes:
        hover_diagnostics: show diagnostics when hovering nodes
    """

    hover_diagnostics: bool = Field(default=False)


class NyxEditorGraphicsStageConfigValues(ConfigValues):
    """Graphics stage config values.

    Attributes:
        nodes: graphics node config values
    """

    nodes: NyxEditorGraphicsNodeConfigValues = Field(
        default_factory=NyxEditorGraphicsNodeConfigValues, alias="nodes"
    )


class NyxEditorWidgetsConfigValues(ConfigValues):
    """Container for nyx editor widget configurations

    Attributes:
        log_widget: log widget config values
    """

    log_widget: NyxEditorLogWidgetConfigValues = Field(
        default_factory=NyxEditorLogWidgetConfigValues, alias="log_widget"
    )
    graphics_stage: NyxEditorGraphicsStageConfigValues = Field(
        default_factory=NyxEditorGraphicsStageConfigValues, alias="graphics_stage"
    )


class NyxEditorBehaviourConfigValues(ConfigValues):
    """Editor behaviour config values.

    Attributes:
        new_stage_on_launch: create an empty stage at startup
        highlight_flow_chain: animate the flow links that are part of the execution
            chain of the drawn scope
    """

    new_stage_on_launch: bool = Field(default=False)
    highlight_flow_chain: bool = Field(default=True)


class NyxEditorSessionConfigValues(ConfigValues):
    """Editor session config values.

    Attributes:
        recent_files: recently used stage files, most recent first
    """

    recent_files: list[str] = Field(default_factory=list)

    def pre_serialize(self) -> None:
        """Drop recent files that no longer exist before saving."""
        self.recent_files = [f for f in self.recent_files if pathlib.Path(f).is_file()]

    def pre_deserialize(self, data: dict) -> dict:
        """Drop recent files that no longer exist while loading.

        Args:
            data (dict): raw config data.

        Returns:
            dict: filtered copy of the data.
        """
        data = dict(data)
        data["recent_files"] = [
            f for f in data.get("recent_files", []) if pathlib.Path(f).is_file()
        ]
        return data


class NyxConfigValues(ConfigValues):
    """Main container for config values.

    Attributes:
        main_window: nyx editor window config values
        editor_style: nyx editor styling config values
        editor_widgets: config values container per widget
        logging_level: logging_level
    """

    main_window: NyxMainWindowConfigValues = Field(
        default_factory=NyxMainWindowConfigValues, alias="main_window"
    )
    editor_behaviour: NyxEditorBehaviourConfigValues = Field(
        default_factory=NyxEditorBehaviourConfigValues, alias="editor_behaviour"
    )
    editor_session: NyxEditorSessionConfigValues = Field(
        default_factory=NyxEditorSessionConfigValues, alias="editor_session"
    )
    editor_style: NyxEditorStyleConfigValues = Field(
        default_factory=NyxEditorStyleConfigValues, alias="editor_style"
    )
    editor_widgets: NyxEditorWidgetsConfigValues = Field(
        default_factory=NyxEditorWidgetsConfigValues, alias="editor_widgets"
    )
    logging_level: int = Field(default=logging.INFO)


class NyxConfig(LayeredConfig[NyxConfigValues]):
    """Nyx layered config.

    Attributes:
        VALUES_CLASS: ConfigValues class to be used with this config
        ROOT_CONFIG_LAYER: Root config layer
    """

    VALUES_CLASS = NyxConfigValues
    ROOT_CONFIG_LAYER = ConfigLayer(name="user", file_path=USER_CONFIG_FILE_PATH)

    def __init__(self):
        """Initialize NyxConfig, registering the root config layer."""
        super().__init__(layer_filter=self.ROOT_CONFIG_LAYER.name)
        self._register_root_layer()

    def _register_root_layer(self):
        """Register the root config layer unless already registered."""
        if self.ROOT_CONFIG_LAYER.name not in self.layer_manager.root_layers:
            self.layer_manager.register(self.ROOT_CONFIG_LAYER)
