from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.editor.core.action_registry import ACTION_REGISTRY
from nyx.editor.core.actions import ActionId
from nyx.editor.widgets.graph_scope_widget import GraphScopeWidget


class StageControlsOverlay(QtWidgets.QFrame):
    """Floating bar over the graph: run button, scope field and inspector toggle.

    The run button executes the stage, and its drop-down menu executes from the selected
    node. The scope field follows the active stage editor.
    """

    BUTTON_HEIGHT = 34
    ICON_SIZE = 20

    def __init__(
        self,
        inspector_action: QtGui.QAction,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize StageControlsOverlay.

        Args:
            inspector_action (QtGui.QAction): checkable action that toggles the
                inspector panel.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._inspector_action = inspector_action
        self.setObjectName("stage_controls_overlay")
        self.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.setAutoFillBackground(True)

        self._create_widgets()
        self._create_layouts()

    def _create_widgets(self) -> None:
        """Create child widgets."""
        icon_size = QtCore.QSize(self.ICON_SIZE, self.ICON_SIZE)

        self.run_button = QtWidgets.QToolButton(self)
        self.run_button.setObjectName("run_button")
        self.run_button.setDefaultAction(ACTION_REGISTRY.action(ActionId.EXECUTE_STAGE))
        self.run_button.setText("Run")
        self.run_button.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.run_button.setPopupMode(
            QtWidgets.QToolButton.ToolButtonPopupMode.MenuButtonPopup
        )
        self.run_button.setIconSize(icon_size)
        self.run_button.setMinimumHeight(self.BUTTON_HEIGHT)
        self.run_button.setMinimumWidth(96)
        self.run_menu = QtWidgets.QMenu(self.run_button)
        self.run_menu.addAction(ACTION_REGISTRY.action(ActionId.EXECUTE_FROM_SELECTED))
        self.run_button.setMenu(self.run_menu)

        self.scope_widget = GraphScopeWidget(self)

        self.inspector_button = QtWidgets.QToolButton(self)
        self.inspector_button.setObjectName("inspector_toggle_button")
        self.inspector_button.setDefaultAction(self._inspector_action)
        self.inspector_button.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        self.inspector_button.setToolTip("Toggle inspector")
        self.inspector_button.setIconSize(icon_size)
        self.inspector_button.setFixedSize(self.BUTTON_HEIGHT, self.BUTTON_HEIGHT)

        for button in (
            self.scope_widget.scope_back_btn,
            self.scope_widget.scope_root_btn,
        ):
            button.setIconSize(icon_size)
            button.setFixedSize(self.BUTTON_HEIGHT, self.BUTTON_HEIGHT)
        self.scope_widget.path_line_edit.setMinimumHeight(self.BUTTON_HEIGHT)

    def _create_layouts(self) -> None:
        """Create layouts."""
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(10)
        main_layout.addWidget(self.run_button)
        main_layout.addWidget(self.scope_widget)
        main_layout.addWidget(self.inspector_button)
