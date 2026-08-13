import logging
from dataclasses import dataclass, field

from json_config.api import ConfigLayer, ConfigValues, LayeredConfig

from .constants import USER_CONFIG_FILE_PATH


@dataclass
class NyxMainWindowConfigValues(ConfigValues):
    size: tuple[int, int] = field(default=(600, 400))
    position: tuple[int, int] = field(default=(0, 0))
    is_always_on_top: bool = field(default=False)


@dataclass
class NyxEditorStyleConfigValues(ConfigValues):
    dark_mode: bool = field(default=True)


@dataclass
class NyxEditorLogWidgetConfigValues(ConfigValues):
    auto_scroll: bool = field(default=True)


@dataclass
class NyxEditorWidgetsConfigValues(ConfigValues):
    log_widget: NyxEditorLogWidgetConfigValues = field(
        default_factory=NyxEditorLogWidgetConfigValues,
        metadata={"category": "log_widget"},
    )

@dataclass
class NyxConfigValues(ConfigValues):
    main_window: NyxMainWindowConfigValues = field(
        default_factory=NyxMainWindowConfigValues, metadata={"category": "main_window"}
    )
    editor_style: NyxEditorStyleConfigValues = field(
        default_factory=NyxEditorStyleConfigValues,
        metadata={"category": "editor_style"},
    )
    editor_widgets: NyxEditorWidgetsConfigValues = field(
        default_factory=NyxEditorWidgetsConfigValues,
        metadata={"category": "editor_widgets"},
    )
    logging_level: int = field(default=logging.INFO)


class NyxConfig(LayeredConfig[NyxConfigValues]):
    VALUES_CLASS = NyxConfigValues
    ROOT_CONFIG_LAYER = ConfigLayer(name="user", file_path=USER_CONFIG_FILE_PATH)

    def __init__(self):
        super().__init__(layer_filter=self.ROOT_CONFIG_LAYER.name)
        self._register_root_layer()

    def _register_root_layer(self):
        if self.ROOT_CONFIG_LAYER.name not in self.layer_manager.root_layers:
            self.layer_manager.register(self.ROOT_CONFIG_LAYER)
