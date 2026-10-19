from __future__ import annotations

import typing

from PySide6 import QtCore, QtGui, QtWidgets

from .output_log_widget import OutputLogWidget

if typing.TYPE_CHECKING:
    from nyx.core.layered_config import NyxConfig


QWIDGETSIZE_MAX_IN_PIXELS = 16777215  # Qt's "no maximum" value


class OutputLogDockWidget(QtWidgets.QDockWidget):
    """Dock holding the output log, remembering the height the user expanded it to."""

    MINIMUM_EXPANDED_EXTRA_HEIGHT = 80
    INITIAL_EXPANDED_HEIGHT = 220

    def __init__(
        self,
        title: str,
        parent_main_window: QtWidgets.QMainWindow,
    ):
        """Initialize OutputLogDockWidget.

        Args:
            title (str): dock title.
            parent_main_window (QtWidgets.QMainWindow): main window the dock belongs to.
        """
        super().__init__(title, parent=parent_main_window)

        self.output_log_widget = OutputLogWidget(parent=self)
        self.setWidget(self.output_log_widget)

        # Hide the dock's own title bar so it looks like a real status bar.
        # The separator between the dock and the central widget stays draggable.
        self.setTitleBarWidget(QtWidgets.QWidget())
        self.setFeatures(self.DockWidgetFeature.DockWidgetClosable)
        self.setAllowedAreas(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea)

        self._last_user_expanded_height = self.INITIAL_EXPANDED_HEIGHT

        # While True, resize events are NOT recorded as user-chosen heights.
        # This covers the startup layout passes and our own resizeDocks call.
        self._is_restore_of_expanded_height_pending = True
        self._is_restoring_expanded_height_programmatically = False

        self.output_log_widget.expansion_state_changed.connect(
            self._apply_size_constraints_for_expansion_state
        )
        self.visibilityChanged.connect(self._on_visibility_changed)

        self._apply_size_constraints_for_expansion_state(
            self.output_log_widget.is_expanded()
        )

    # ---- Config ----
    def apply_config_values(self, config: NyxConfig) -> None:
        """Apply stored values.

        Call this BEFORE the main window builds or restores its dock layout,
        so the size constraints already reflect the expansion state when Qt
        places the dock.
        """
        config_values = config.values.editor_widgets.log_widget
        self._last_user_expanded_height = config_values.expanded_height
        self._is_restore_of_expanded_height_pending = True
        self.output_log_widget.set_expanded(config_values.is_expanded)
        # set_expanded may not emit expansion_state_changed when the state is
        # unchanged, so always apply the constraints explicitly.
        self._apply_size_constraints_for_expansion_state(
            self.output_log_widget.is_expanded()
        )

    def save_config_values(self, config: NyxConfig) -> None:
        """Store the expansion state and height in the config.

        Args:
            config (NyxConfig): config to update.
        """
        config_values = config.values.editor_widgets.log_widget
        config_values.expanded_height = self._last_user_expanded_height
        config_values.is_expanded = self.output_log_widget.is_expanded()

    # ---- Sizing ----
    def sizeHint(self) -> QtCore.QSize:
        """QtCore.QSize: preferred size, using the last expanded height when expanded."""
        # Used by QMainWindow when it places the dock without a saved size.
        base_size_hint = super().sizeHint()
        if self.output_log_widget.is_expanded():
            return QtCore.QSize(base_size_hint.width(), self._last_user_expanded_height)
        return base_size_hint

    def _minimum_expanded_height_in_pixels(self) -> int:
        """int: smallest height the expanded log can have."""
        return (
            self.output_log_widget.header_height_in_pixels()
            + self.MINIMUM_EXPANDED_EXTRA_HEIGHT
        )

    def _apply_size_constraints_for_expansion_state(self, is_expanded: bool) -> None:
        """Pin the log to its header height when collapsed and free it when expanded.

        Args:
            is_expanded (bool): whether the log is expanded.
        """
        if not is_expanded:
            collapsed_height_in_pixels = self.output_log_widget.header_height_in_pixels()
            self.output_log_widget.setMinimumHeight(collapsed_height_in_pixels)
            self.output_log_widget.setMaximumHeight(collapsed_height_in_pixels)
            return

        # Expanded: unpin the height so the separator can be dragged.
        self.output_log_widget.setMinimumHeight(
            self._minimum_expanded_height_in_pixels()
        )
        self.output_log_widget.setMaximumHeight(QWIDGETSIZE_MAX_IN_PIXELS)
        self.updateGeometry()
        self._is_restore_of_expanded_height_pending = True
        self.schedule_restore_of_expanded_height()

    # ---- Deferred height restore ----
    def schedule_restore_of_expanded_height(self) -> None:
        """Restore the expanded height on the next event-loop turn."""
        QtCore.QTimer.singleShot(
            0, self.restore_expanded_height_into_main_window_if_possible
        )

    def _on_visibility_changed(self, is_visible: bool) -> None:
        """Restore a pending expanded height once the dock becomes visible.

        Args:
            is_visible (bool): dock visibility.
        """
        if is_visible and self._is_restore_of_expanded_height_pending:
            self.schedule_restore_of_expanded_height()

    def restore_expanded_height_into_main_window_if_possible(self) -> None:
        """Resize the dock to the last user height if it is expanded and visible."""
        if not self.output_log_widget.is_expanded():
            return

        parent_main_window = self.parentWidget()
        if not isinstance(parent_main_window, QtWidgets.QMainWindow):
            return

        if not self.isVisible():
            # Hidden docks are not part of the main window layout, so
            # resizeDocks would be a no-op. visibilityChanged calls us again
            # when the dock is shown.
            return

        self._is_restoring_expanded_height_programmatically = True
        parent_main_window.resizeDocks(
            [self],
            [self._last_user_expanded_height],
            QtCore.Qt.Orientation.Vertical,
        )
        # Qt applies the new layout on a later event-loop turn, so keep
        # ignoring resize events until then. Otherwise intermediate sizes
        # would overwrite the remembered height.
        QtCore.QTimer.singleShot(0, self._finish_programmatic_restore_of_expanded_height)

    def _finish_programmatic_restore_of_expanded_height(self) -> None:
        """Clear the flags set while restoring the height."""
        self._is_restoring_expanded_height_programmatically = False
        self._is_restore_of_expanded_height_pending = False

    def resizeEvent(self, resize_event: QtGui.QResizeEvent) -> None:
        """Remember the height the user resized the expanded dock to.

        Args:
            resize_event (QtGui.QResizeEvent): event.
        """
        super().resizeEvent(resize_event)

        if not self.output_log_widget.is_expanded():
            return

        # Ignore startup layout passes and our own programmatic resizes.
        if (
            not self.isVisible()
            or self._is_restore_of_expanded_height_pending
            or self._is_restoring_expanded_height_programmatically
        ):
            return

        # Remember the height only while expanded, ignoring transitional
        # sizes below the expanded minimum.
        current_height_in_pixels = self.height()
        if current_height_in_pixels >= self._minimum_expanded_height_in_pixels():
            self._last_user_expanded_height = current_height_in_pixels
