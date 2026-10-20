from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues

from nyx.core.config_values.graphics_values import NyxEditorGraphicsStageConfigValues


class NyxEditorLogWidgetConfigValues(NyxBaseConfigValues):
    """Logger widget config values."""

    auto_scroll: bool = Field(default=True)
    """Scroll the log to new records."""
    expanded_height: int = Field(default=220)
    """Height of the expanded log dock in pixels."""
    is_expanded: bool = Field(default=False)
    """The log dock is expanded."""


class NyxEditorWidgetsConfigValues(NyxBaseConfigValues):
    """Container for nyx editor widget configurations"""

    log_widget: NyxEditorLogWidgetConfigValues = Field(
        default_factory=NyxEditorLogWidgetConfigValues, alias="log_widget"
    )
    """Log widget settings."""
    graphics_stage: NyxEditorGraphicsStageConfigValues = Field(
        default_factory=NyxEditorGraphicsStageConfigValues, alias="graphics_stage"
    )
    """Graphics stage settings."""
