from __future__ import annotations

import typing

from PySide6 import QtCore, QtGui

from .overlay_panel import OverlayPanel
from .panel_host import PanelHost
from .panel_registry import PANEL_REGISTRY, PanelRegistry
from .panel_sidebar import PanelSidebar

if typing.TYPE_CHECKING:
    from nyx.core.layered_config import NyxConfig
    from nyx.editor.main_window import NyxEditorMainWindow


class PanelManager(QtCore.QObject):
    """Opens and closes the overlay panels and keeps the sidebar and menus in sync.

    Panels are created from their definition the first time they are opened. Only one
    panel is open per area.

    Attributes:
        panel_toggled: emitted with the panel id and whether it is open.
    """

    panel_toggled = QtCore.Signal(str, bool)

    def __init__(
        self,
        main_window: NyxEditorMainWindow,
        host: PanelHost,
        sidebar: PanelSidebar,
        registry: PanelRegistry = PANEL_REGISTRY,
    ) -> None:
        """Initialize PanelManager.

        Args:
            main_window (NyxEditorMainWindow): window the panels belong to.
            host (PanelHost): host the panels are attached to.
            sidebar (PanelSidebar): sidebar of the panel buttons.
            registry (PanelRegistry): panel definitions.
        """
        super().__init__(main_window)
        self._main_window = main_window
        self._host = host
        self._sidebar = sidebar
        self._registry = registry
        self._panels: dict[str, OverlayPanel] = {}
        self._pending_sizes: dict[str, int] = {}
        self._actions: dict[str, QtGui.QAction] = {}

        self._create_actions()
        self._sidebar.panel_clicked.connect(self.set_open)

    def _create_actions(self) -> None:
        """Create a checkable toggle action per panel."""
        for definition in self._registry.definitions():
            action = QtGui.QAction(definition.title, self)
            action.setCheckable(True)
            action.setIcon(QtGui.QIcon(definition.icon_path))
            action.triggered.connect(
                lambda checked, panel_id=definition.panel_id: self.set_open(
                    panel_id, checked
                )
            )
            self._actions[definition.panel_id] = action

    def toggle_action(self, panel_id: str) -> QtGui.QAction:
        """Get the checkable action of a panel.

        Args:
            panel_id (str): id of the panel.

        Returns:
            QtGui.QAction: action that toggles the panel.
        """
        return self._actions[panel_id]

    def panel(self, panel_id: str) -> OverlayPanel | None:
        """Get a panel, creating it if needed.

        Args:
            panel_id (str): id of the panel.

        Returns:
            OverlayPanel | None: panel, None if the id is not registered.
        """
        existing_panel = self._panels.get(panel_id)
        if existing_panel is not None:
            return existing_panel
        definition = self._registry.get(panel_id)
        if definition is None:
            return None
        panel = OverlayPanel(
            definition.title,
            definition.area,
            definition.factory(self._main_window),
        )
        panel.close_requested.connect(lambda: self.set_open(panel_id, False))
        panel.size_requested.connect(lambda size: self._host.set_panel_size(panel, size))
        self._host.attach_panel(panel, self._pending_sizes.get(panel_id))
        self._panels[panel_id] = panel
        return panel

    def is_open(self, panel_id: str) -> bool:
        """Check whether a panel is open.

        Args:
            panel_id (str): id of the panel.

        Returns:
            bool: panel is open.
        """
        panel = self._panels.get(panel_id)
        return panel is not None and not panel.isHidden()

    def open_panel_ids(self) -> list[str]:
        """list[str]: ids of the open panels."""
        return [panel_id for panel_id in self._panels if self.is_open(panel_id)]

    def toggle(self, panel_id: str) -> None:
        """Open a closed panel, close an open one.

        Args:
            panel_id (str): id of the panel.
        """
        self.set_open(panel_id, not self.is_open(panel_id))

    def set_open(self, panel_id: str, is_open: bool) -> None:
        """Open or close a panel. Opening closes the other panel of its area.

        Args:
            panel_id (str): id of the panel.
            is_open (bool): panel should be open.
        """
        definition = self._registry.get(panel_id)
        if definition is None:
            return
        changed_ids = []
        if is_open:
            panel = self.panel(panel_id)
            for other_definition in self._registry.definitions():
                if (
                    other_definition.panel_id != panel_id
                    and other_definition.area is definition.area
                    and self.is_open(other_definition.panel_id)
                ):
                    self._panels[other_definition.panel_id].hide()
                    changed_ids.append(other_definition.panel_id)
            if panel.isHidden():
                panel.show()
                changed_ids.append(panel_id)
        elif self.is_open(panel_id):
            self._panels[panel_id].hide()
            changed_ids.append(panel_id)
        self._host.update_layout()
        for changed_id in changed_ids:
            self._sync(changed_id)
        if not is_open or panel_id not in changed_ids:
            # Keep the clicked button honest when the request changed nothing
            self._sync(panel_id)
        # Syncing can resize the floating widgets, for example the stage controls overlay
        self._host.update_layout()

    def _sync(self, panel_id: str) -> None:
        """Show the open state of a panel in the sidebar and the actions.

        Args:
            panel_id (str): id of the panel.
        """
        is_open = self.is_open(panel_id)
        self._sidebar.set_panel_checked(panel_id, is_open)
        # `setChecked` emits `toggled` but not `triggered`, which the user clicks use
        self._actions[panel_id].setChecked(is_open)
        self.panel_toggled.emit(panel_id, is_open)

    # Config
    def save_config_values(self, config: NyxConfig) -> None:
        """Store the hidden buttons, open panels and sizes in the config.

        Args:
            config (NyxConfig): config to update.
        """
        panels_config = config.values.main_window.panels
        panels_config.hidden_buttons = self._sidebar.hidden_button_ids()
        panels_config.open_panels = self.open_panel_ids()
        sizes = dict(self._pending_sizes)
        for panel_id, panel in self._panels.items():
            sizes[panel_id] = self._host.panel_size(panel)
        panels_config.sizes = sizes

    def apply_config_values(self, config: NyxConfig) -> None:
        """Apply the hidden buttons, open panels and sizes of the config.

        Args:
            config (NyxConfig): config to read.
        """
        panels_config = config.values.main_window.panels
        self._pending_sizes = dict(panels_config.sizes)
        for panel_id, panel in self._panels.items():
            if panel_id in self._pending_sizes:
                self._host.set_panel_size(panel, self._pending_sizes[panel_id])
        self._sidebar.set_hidden_buttons(panels_config.hidden_buttons)
        for panel_id in panels_config.open_panels:
            self.set_open(panel_id, True)
