import logging

from pydantic.dataclasses import Field
from json_config.api import ConfigLayer, ConfigValues, LayeredConfig

from ..static.paths import USER_CONFIG_FILE_PATH


class NyxMainWindowConfigValues(ConfigValues):
    """Main window config values.

    Attributes:
        size: window size
        position: window position
        is_always_on_top: window stays on top
    """

    size: tuple[int, int] = Field(default=(600, 400))
    position: tuple[int, int] = Field(default=(0, 0))
    is_always_on_top: bool = Field(default=False)


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


class NyxEditorWidgetsConfigValues(ConfigValues):
    """Container for nyx editor widget configurations

    Attributes:
        log_widget: log widget config values
    """

    log_widget: NyxEditorLogWidgetConfigValues = Field(
        default_factory=NyxEditorLogWidgetConfigValues, alias="log_widget"
    )


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
        super().__init__(layer_filter=self.ROOT_CONFIG_LAYER.name)
        self._register_root_layer()

    def _register_root_layer(self):
        if self.ROOT_CONFIG_LAYER.name not in self.layer_manager.root_layers:
            self.layer_manager.register(self.ROOT_CONFIG_LAYER)
