from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues

from nyx.core.config_values.animation_values import NyxEditorAnimationConfigValues


class NyxEditorStyleConfigValues(NyxBaseConfigValues):
    """Editor styling config values."""

    dark_mode: bool = Field(default=True)
    """Use the dark palette."""
    animations: NyxEditorAnimationConfigValues = Field(
        default_factory=NyxEditorAnimationConfigValues, alias="animations"
    )
    """Animation settings."""
