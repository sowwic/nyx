from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues


class NyxMainWindowLayoutConfigValues(NyxBaseConfigValues):
    """Main window dock layout config values."""

    version: int = Field(default=0)
    """Layout version the state was saved with."""
    state: str | None = Field(default=None)
    """Base64 encoded Qt window state."""


class NyxMainWindowConfigValues(NyxBaseConfigValues):
    """Main window config values."""

    size: tuple[int, int] | None = Field(default=None)
    """Window size in pixels."""
    position: tuple[int, int] | None = Field(default=None)
    """Window position on the screen."""
    is_always_on_top: bool = Field(default=False)
    """Keep the window above other windows."""
    layout: NyxMainWindowLayoutConfigValues = Field(
        default_factory=NyxMainWindowLayoutConfigValues, alias="layout"
    )
    """Dock layout of the window."""
