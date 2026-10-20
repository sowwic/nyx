from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues
from nyx.static.enums import LinkAnimationStyle


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
    highlight_flow_chain_style: str = Field(default=LinkAnimationStyle.PULSE.value)
    """Animation that highlights the execution chain, one of: pulse, glow."""
