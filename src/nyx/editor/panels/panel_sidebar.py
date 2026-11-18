from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.editor.core.action_registry import ACTION_REGISTRY

from .panel_registry import PanelDefinition, PanelRegistry, SidebarActionDefinition


class PanelSidebar(QtWidgets.QFrame):
    """Vertical rail of icon buttons that open and close the panels.

    Right-click the rail to choose which panel buttons are shown.

    Attributes:
        panel_clicked: emitted with the panel id and the new checked state when the
            user clicks a button.
        visible_buttons_changed: emitted when the user shows or hides a button.
    """

    BUTTON_WIDTH = 64
    ICON_SIZE = 24

    panel_clicked = QtCore.Signal(str, bool)
    visible_buttons_changed = QtCore.Signal()

    def __init__(
        self, registry: PanelRegistry, parent: QtWidgets.QWidget | None = None
    ) -> None:
        """Initialize PanelSidebar.

        Args:
            registry (PanelRegistry): panels the sidebar can show a button for.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._registry = registry
        self._buttons: dict[str, QtWidgets.QToolButton] = {}
        # Title of every button, panels and actions alike
        self._titles: dict[str, str] = {}
        self._persistent_ids: set[str] = set()
        self.setObjectName("panel_sidebar")
        self.setFixedWidth(self.BUTTON_WIDTH)
        self.setAutoFillBackground(True)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)

        self._create_layouts()
        self._create_connections()
        self.rebuild()

    def _create_layouts(self) -> None:
        """Create layouts."""
        self._top_layout = QtWidgets.QVBoxLayout()
        self._top_layout.setSpacing(2)
        self._bottom_layout = QtWidgets.QVBoxLayout()
        self._bottom_layout.setSpacing(2)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 4, 0, 4)
        main_layout.addLayout(self._top_layout)
        main_layout.addStretch(1)
        main_layout.addLayout(self._bottom_layout)

    def _create_connections(self) -> None:
        """Create signal-slot connections."""
        self.customContextMenuRequested.connect(self._show_context_menu)

    def rebuild(self) -> None:
        """Create a button for every registered panel and action that has none yet."""
        for definition in self._registry.definitions():
            if not definition.has_sidebar_button or definition.panel_id in self._buttons:
                continue
            button = self._create_button(definition)
            button.clicked.connect(
                lambda checked, panel_id=definition.panel_id: self.panel_clicked.emit(
                    panel_id, checked
                )
            )
            self._add_button(
                definition.panel_id,
                definition.title,
                button,
                definition.is_persistent,
            )
        for action_definition in self._registry.action_buttons():
            if action_definition.button_id in self._buttons:
                continue
            button = self._create_action_button(action_definition)
            self._add_button(
                action_definition.button_id,
                action_definition.title,
                button,
                action_definition.is_persistent,
            )

    def _add_button(
        self,
        button_id: str,
        title: str,
        button: QtWidgets.QToolButton,
        is_persistent: bool,
    ) -> None:
        """Put a button in the sidebar.

        Args:
            button_id (str): id of the panel or action button.
            title (str): title shown in the context menu.
            button (QtWidgets.QToolButton): button to add.
            is_persistent (bool): the button is always shown, in the bottom group.
        """
        layout = self._bottom_layout if is_persistent else self._top_layout
        layout.addWidget(button)
        self._buttons[button_id] = button
        self._titles[button_id] = title
        if is_persistent:
            self._persistent_ids.add(button_id)

    def _create_action_button(
        self, definition: SidebarActionDefinition
    ) -> QtWidgets.QToolButton:
        """Create the button of an action.

        Args:
            definition (SidebarActionDefinition): action the button triggers.

        Returns:
            QtWidgets.QToolButton: button that triggers the action when clicked and
                lists the menu actions of the definition when right-clicked.
        """
        button = self._new_button(
            f"sidebar_action_{definition.button_id}",
            definition.title,
            definition.icon_path,
        )
        if definition.menu_action_ids:
            # Qt shows the actions of the button as its context menu
            button.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)
            for action_id in definition.menu_action_ids:
                button.addAction(ACTION_REGISTRY.action(action_id))
        button.clicked.connect(
            lambda _checked=False, action_id=definition.action_id: (
                ACTION_REGISTRY.action(action_id).trigger()
            )
        )
        return button

    def _new_button(
        self, object_name: str, title: str, icon_path: str
    ) -> QtWidgets.QToolButton:
        """Create a sidebar button with the icon above its title.

        Args:
            object_name (str): object name.
            title (str): text and tooltip.
            icon_path (str): resource path of the icon.

        Returns:
            QtWidgets.QToolButton: button.
        """
        button = QtWidgets.QToolButton(self)
        button.setObjectName(object_name)
        button.setText(title)
        button.setToolTip(title)
        button.setIcon(QtGui.QIcon(icon_path))
        button.setIconSize(QtCore.QSize(self.ICON_SIZE, self.ICON_SIZE))
        button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        button.setAutoRaise(True)
        button.setFixedWidth(self.BUTTON_WIDTH)
        return button

    def _create_button(self, definition: PanelDefinition) -> QtWidgets.QToolButton:
        """Create the button of a panel.

        Args:
            definition (PanelDefinition): panel the button toggles.

        Returns:
            QtWidgets.QToolButton: checkable button.
        """
        button = self._new_button(
            f"panel_button_{definition.panel_id}", definition.title, definition.icon_path
        )
        button.setCheckable(True)
        return button

    def button(self, panel_id: str) -> QtWidgets.QToolButton | None:
        """Get the button of a panel.

        Args:
            panel_id (str): id of the panel.

        Returns:
            QtWidgets.QToolButton | None: button, None if the panel is unknown.
        """
        return self._buttons.get(panel_id)

    def set_panel_checked(self, panel_id: str, is_checked: bool) -> None:
        """Show the open state of a panel without emitting `panel_clicked`.

        Args:
            panel_id (str): id of the panel.
            is_checked (bool): panel is open.
        """
        button = self._buttons.get(panel_id)
        if button is not None:
            button.setChecked(is_checked)

    def visible_button_ids(self) -> list[str]:
        """list[str]: ids of the panels and actions that have a visible button."""
        return [
            panel_id
            for panel_id, button in self._buttons.items()
            if not button.isHidden()
        ]

    def hidden_button_ids(self) -> list[str]:
        """list[str]: ids of the hidden buttons. Persistent buttons are never hidden."""
        return [
            button_id for button_id, button in self._buttons.items() if button.isHidden()
        ]

    def set_hidden_buttons(self, button_ids: list[str] | None) -> None:
        """Hide the buttons of the given ids and show the others.

        Buttons that are not in the list are shown, so a button added later is not hidden
        by a list saved earlier. Persistent buttons stay shown.

        Args:
            button_ids (list[str] | None): ids of the buttons to hide. None shows all.
        """
        hidden_ids = button_ids or []
        for button_id, button in self._buttons.items():
            button.setVisible(
                button_id in self._persistent_ids or button_id not in hidden_ids
            )

    def is_persistent(self, button_id: str) -> bool:
        """Check whether a button is always shown.

        Args:
            button_id (str): id of the panel or action.

        Returns:
            bool: the button can't be hidden.
        """
        return button_id in self._persistent_ids

    def _show_context_menu(self, point: QtCore.QPoint) -> None:
        """Show the menu that toggles the panel buttons.

        Args:
            point (QtCore.QPoint): position in the sidebar.
        """
        self._create_context_menu().exec(self.mapToGlobal(point))

    def _create_context_menu(self) -> QtWidgets.QMenu:
        """Create the menu that toggles the buttons that can be hidden.

        Returns:
            QtWidgets.QMenu: menu with a checkable action per such button.
        """
        menu = QtWidgets.QMenu(self)
        menu.addSection("Sidebar buttons")
        for button_id, title in self._titles.items():
            if button_id in self._persistent_ids:
                continue
            action = menu.addAction(title)
            action.setCheckable(True)
            action.setChecked(not self._buttons[button_id].isHidden())
            action.toggled.connect(
                lambda checked, button_id=button_id: self._set_button_visible(
                    button_id, checked
                )
            )
        return menu

    def _set_button_visible(self, panel_id: str, is_visible: bool) -> None:
        """Show or hide one button on behalf of the user.

        Args:
            panel_id (str): id of the panel.
            is_visible (bool): button is shown.
        """
        if panel_id in self._persistent_ids:
            return
        self._buttons[panel_id].setVisible(is_visible)
        self.visible_buttons_changed.emit()
