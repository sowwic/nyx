from __future__ import annotations

import typing
import logging

from PySide6 import QtCore, QtWidgets

from nyx.core.plugin_subsystem.registry import NYX_REGISTRY
from nyx.static.enums import CoreInspectorWidgets
from .inspector_widgets.base import InspectorWidget

if typing.TYPE_CHECKING:
    from nyx.core.stage_object import StageObject
    from ..main_window import NyxEditorMainWindow
    from .stage_graph_editor import StageGraphEditor

LOGGER = logging.getLogger(__name__)


class Inspector(QtWidgets.QWidget):
    """Panel content showing the selected stage object.

    The object picks the widget that shows it with `get_inspector_widget_id`. Widgets
    come from the registry, the inspector creates each one when it is first needed and
    keeps it. Objects without a widget get a placeholder text.
    """

    def __init__(
        self, main_window: NyxEditorMainWindow, parent: QtWidgets.QWidget | None = None
    ) -> None:
        """Initialize Inspector.

        Args:
            main_window (NyxEditorMainWindow): editor main window.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self.main_window: NyxEditorMainWindow = main_window
        self._widgets: dict[str, InspectorWidget] = {}
        self._unknown_widget_ids: set[str] = set()
        self._active_widget: InspectorWidget | None = None

        self.create_actions()
        self.create_widgets()
        self.create_layouts()

    def create_actions(self):
        """Create actions. The inspector has none."""
        pass

    def create_widgets(self):
        """Create the placeholder and the widget showing nodes."""
        self._placeholder = QtWidgets.QLabel()
        self._placeholder.setObjectName("inspector_placeholder")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setWordWrap(True)
        self._placeholder.setEnabled(False)

    def create_layouts(self):
        """Stack the placeholder and the widgets."""
        self.main_layout = QtWidgets.QStackedLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self._placeholder)
        # Created now, so the node widgets exist before the first selection
        self._get_widget(CoreInspectorWidgets.NODE)
        self.main_layout.setCurrentWidget(self._placeholder)

    @property
    def current_stage_graph(self) -> StageGraphEditor | None:
        """StageGraphEditor | None: editor of the active window."""
        return self.main_window.current_stage_graph

    @property
    def active_widget(self) -> InspectorWidget | None:
        """InspectorWidget | None: widget shown, None while the placeholder is."""
        return self._active_widget

    @property
    def placeholder_text(self) -> str:
        """str: text of the placeholder."""
        return self._placeholder.text()

    def _get_widget(self, widget_id: str) -> InspectorWidget | None:
        """Get the widget of an id, creating it the first time.

        Args:
            widget_id (str): inspector widget id.

        Returns:
            InspectorWidget | None: widget, None if no widget is registered with the id.
        """
        widget = self._widgets.get(widget_id)
        if widget is not None:
            return widget
        widget_cls = NYX_REGISTRY.get_inspector_widget_cls(widget_id)
        if widget_cls is None:
            if widget_id not in self._unknown_widget_ids:
                self._unknown_widget_ids.add(widget_id)
                LOGGER.error("Unknown inspector widget %r", widget_id)
            return None
        widget = widget_cls()
        self._widgets[widget_id] = widget
        self.main_layout.addWidget(widget)
        return widget

    def _show_widget(self, widget: InspectorWidget | None) -> None:
        """Show a widget, or the placeholder.

        The widget shown before is told to show no object, so it lets go of it.

        Args:
            widget (InspectorWidget | None): widget to show, None for the placeholder.
        """
        previous = self._active_widget
        # Set before telling the previous widget, which can push a command that makes
        # the inspector update again
        self._active_widget = widget
        self.main_layout.setCurrentWidget(
            self._placeholder if widget is None else widget
        )
        if previous is not None and previous is not widget:
            previous.set_stage_object(None)

    def clear(self):
        """Show no object."""
        for widget in self._widgets.values():
            widget.set_stage_object(None)
        self._active_widget = None
        self._placeholder.setText("Nothing to inspect.")
        self.main_layout.setCurrentWidget(self._placeholder)

    def show_stage_object(self, stage_object: StageObject) -> None:
        """Show an object with the widget of its type.

        Args:
            stage_object (StageObject): object to show.
        """
        widget_id = type(stage_object).get_inspector_widget_id()
        if widget_id is None:
            self._show_widget(None)
            self._placeholder.setText(
                f"No inspector available for {self._type_name(stage_object)}."
            )
            return
        widget = self._get_widget(widget_id)
        if widget is None:
            self._show_widget(None)
            self._placeholder.setText(
                f"Inspector widget {widget_id!r} is not available."
            )
            return
        self._show_widget(widget)
        widget.set_stage_object(stage_object)

    @staticmethod
    def _type_name(stage_object: StageObject) -> str:
        """Get a name of the type of an object to show to the user.

        Args:
            stage_object (StageObject): object.

        Returns:
            str: display name of the type, the class name if it has none.
        """
        try:
            return stage_object.get_type_display_name()
        except AttributeError, NotImplementedError:
            return type(stage_object).__name__

    def update_data(self):
        """Show the selected object of the active editor, or the root node."""
        graph = self.current_stage_graph
        if graph is None:
            self.clear()
            self.setEnabled(False)
            return

        self.setEnabled(True)
        selected_objects = graph.list_selected_objects()
        self.show_stage_object(
            selected_objects[0] if selected_objects else graph.stage.root_node
        )
