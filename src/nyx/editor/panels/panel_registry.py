from __future__ import annotations

import dataclasses
import enum
import typing

if typing.TYPE_CHECKING:
    from PySide6 import QtWidgets

    from nyx.editor.main_window import NyxEditorMainWindow


class PanelArea(enum.StrEnum):
    """Edge of the graph area an overlay panel is attached to."""

    LEFT = "left"
    RIGHT = "right"
    BOTTOM = "bottom"


@dataclasses.dataclass(frozen=True)
class PanelDefinition:
    """Describes an overlay panel that the sidebar can open.

    Attributes:
        panel_id: unique id, stored in the config.
        title: title shown in the panel header and the sidebar button.
        icon_path: resource path of the sidebar icon.
        factory: creates the panel content from the main window. Called once, when the
            panel is first needed.
        area: edge of the graph area the panel is attached to.
        has_sidebar_button: give the panel a sidebar button. Panels without one are
            opened by their toggle action, for example from a floating widget.
        is_persistent: the sidebar button is always shown, in the bottom group, and
            can't be hidden. Other buttons are in the top group and can be hidden.
    """

    panel_id: str
    title: str
    icon_path: str
    factory: typing.Callable[[NyxEditorMainWindow], QtWidgets.QWidget]
    area: PanelArea = PanelArea.LEFT
    has_sidebar_button: bool = True
    is_persistent: bool = False


@dataclasses.dataclass(frozen=True)
class SidebarActionDefinition:
    """Describes a sidebar button that triggers an action instead of opening a panel.

    Attributes:
        button_id: unique id, stored in the config together with the panel ids.
        title: title shown below the icon.
        icon_path: resource path of the icon.
        action_id: id of the editor action the button triggers when it is clicked.
        menu_action_ids: ids of the editor actions listed in the menu that right-clicking
            the button opens. Empty for a button without one.
        is_persistent: the button is always shown, in the bottom group, and can't be
            hidden. Other buttons are in the top group and can be hidden.
    """

    button_id: str
    title: str
    icon_path: str
    action_id: str
    menu_action_ids: tuple[str, ...] = ()
    is_persistent: bool = True


class PanelRegistry:
    """Ordered collection of the panel and sidebar action definitions."""

    def __init__(self) -> None:
        """Initialize PanelRegistry."""
        self._definitions: dict[str, PanelDefinition] = {}
        self._action_buttons: dict[str, SidebarActionDefinition] = {}

    def register_action_button(self, definition: SidebarActionDefinition) -> None:
        """Register a sidebar button that triggers an action, replacing the same id.

        Args:
            definition (SidebarActionDefinition): button to register.
        """
        self._action_buttons[definition.button_id] = definition

    def action_buttons(self) -> list[SidebarActionDefinition]:
        """list[SidebarActionDefinition]: registered action buttons, in order."""
        return list(self._action_buttons.values())

    def register(self, definition: PanelDefinition) -> None:
        """Register a panel, replacing the one with the same id.

        Args:
            definition (PanelDefinition): panel to register.
        """
        self._definitions[definition.panel_id] = definition

    def unregister(self, panel_id: str) -> None:
        """Remove a panel.

        Args:
            panel_id (str): id of the panel. Unknown ids are ignored.
        """
        self._definitions.pop(panel_id, None)

    def get(self, panel_id: str) -> PanelDefinition | None:
        """Get a definition.

        Args:
            panel_id (str): id of the panel.

        Returns:
            PanelDefinition | None: definition, None if not registered.
        """
        return self._definitions.get(panel_id)

    def definitions(self) -> list[PanelDefinition]:
        """list[PanelDefinition]: registered panels, in registration order."""
        return list(self._definitions.values())


PANEL_REGISTRY = PanelRegistry()
