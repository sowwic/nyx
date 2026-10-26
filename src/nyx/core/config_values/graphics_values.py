from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues
from nyx.static.enums import LinkAnimationStyle, LinkStyle, StageBackGroundStyle
from nyx.static.vars import DEFAULT_GROUP_COLOR, DEFAULT_NOTE_COLOR


class NyxEditorGraphicsNodeConfigValues(NyxBaseConfigValues):
    """Graphics node config values."""

    hover_diagnostics: bool = Field(default=False)
    """Show the model roles as a tooltip when hovering nodes and plugs."""


class NyxEditorGraphicsStageConfigValues(NyxBaseConfigValues):
    """Graphics stage config values."""

    nodes: NyxEditorGraphicsNodeConfigValues = Field(
        default_factory=NyxEditorGraphicsNodeConfigValues, alias="nodes"
    )
    """Graphics node settings."""
    viewport_debug_overlay: bool = Field(default=False)
    """Show performance numbers over the graph views."""
    highlight_flow_chain: bool = Field(default=True)
    """Animate the flow links that are part of the execution chain of the drawn scope."""
    link_style: str = Field(default=LinkStyle.BEZIER.value)
    """Shape the links are drawn with, one of: bezier, direct, square."""
    highlight_flow_chain_style: str = Field(default=LinkAnimationStyle.PULSE.value)
    """Animation that highlights the execution chain, one of: pulse, glow."""
    background_style: str = Field(default=StageBackGroundStyle.GRID.value)
    """Pattern the stage background is drawn with, one of: grid, dots."""
    background_color: str = Field(default="#393939")
    """Color the stage background is filled with, as a hex color such as #393939."""
    default_note_color: str = Field(default=DEFAULT_NOTE_COLOR)
    """Color new notes get, as a hex color such as #e8c95a."""
    default_group_color: str = Field(default=DEFAULT_GROUP_COLOR)
    """Color new groups get, as a hex color such as #5b8def."""
