from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues


class NyxEditorLinkPulseAnimationConfigValues(NyxBaseConfigValues):
    """Link pulse animation config values."""

    color: str = Field(default="#4BE3FF")
    """Color of the dot and its tail, a color name or #RRGGBB."""
    speed: float = Field(default=160.0)
    """Scene units the dot travels per second."""
    radius: int = Field(default=5)
    """Radius of the dot in scene units."""
    tail_samples: int = Field(default=6)
    """Number of dots the tail is made of."""
    tail_step: float = Field(default=6.0)
    """Scene units between the dots of the tail."""


class NyxEditorLinkGlowAnimationConfigValues(NyxBaseConfigValues):
    """Link glow animation config values."""

    color: str = Field(default="#4BE3FF")
    """Color of the halo, a color name or #RRGGBB."""
    period: float = Field(default=1.6)
    """Seconds for the glow to swell and fade once."""
    layers: tuple[tuple[float, float], ...] = Field(
        default=((12.0, 0.15), (8.0, 0.25), (4.0, 0.4))
    )
    """Strokes the halo is made of, as (width, opacity) pairs. The width is in scene
    units, the opacity is the one at full intensity."""


class NyxEditorAnimationConfigValues(NyxBaseConfigValues):
    """Animation config values."""

    link_pulse: NyxEditorLinkPulseAnimationConfigValues = Field(
        default_factory=NyxEditorLinkPulseAnimationConfigValues, alias="link_pulse"
    )
    """Settings of the link pulse animation."""
    link_glow: NyxEditorLinkGlowAnimationConfigValues = Field(
        default_factory=NyxEditorLinkGlowAnimationConfigValues, alias="link_glow"
    )
    """Settings of the link glow animation."""
