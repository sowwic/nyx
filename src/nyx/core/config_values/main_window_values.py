from pydantic.dataclasses import Field

from nyx.core.config_values.base_values import NyxBaseConfigValues


class NyxMainWindowPanelsConfigValues(NyxBaseConfigValues):
    """Main window sidebar and overlay panel config values."""

    hidden_buttons: list[str] | None = Field(default=None)
    """Ids of the sidebar buttons the user hid. Null shows the default ones."""
    open_panels: list[str] = Field(default_factory=list)
    """Ids of the panels that are open."""
    sizes: dict[str, int] = Field(default_factory=dict)
    """Size of each panel in pixels (width or height, depending on its edge)."""


class NyxMainWindowConfigValues(NyxBaseConfigValues):
    """Main window config values."""

    size: tuple[int, int] | None = Field(default=None)
    """Window size in pixels."""
    position: tuple[int, int] | None = Field(default=None)
    """Window position on the screen."""
    is_always_on_top: bool = Field(default=False)
    """Keep the window above other windows."""
    panels: NyxMainWindowPanelsConfigValues = Field(
        default_factory=NyxMainWindowPanelsConfigValues, alias="panels"
    )
    """Sidebar and overlay panels of the window."""
