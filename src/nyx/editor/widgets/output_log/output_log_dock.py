from PySide6 import QtCore, QtWidgets

from .output_log_widget import OutputLogWidget

QWIDGETSIZE_MAX_IN_PIXELS = 16777215  # Qt's "no maximum" value


class OutputLogDockWidget(QtWidgets.QDockWidget):
    MINIMUM_EXPANDED_EXTRA_HEIGHT_IN_PIXELS = 80
    INITIAL_EXPANDED_HEIGHT_IN_PIXELS = 220

    def __init__(
        self,
        title: str,
        parent_main_window: QtWidgets.QMainWindow,
    ):
        super().__init__(title, parent=parent_main_window)

        self.output_log_widget = OutputLogWidget(parent=self)
        self.setWidget(self.output_log_widget)

        # Hide the dock's own title bar so it looks like a real status bar.
        # The separator between the dock and the central widget stays draggable.
        self.setTitleBarWidget(QtWidgets.QWidget())
        self.setFeatures(self.DockWidgetFeature.DockWidgetClosable)
        self.setAllowedAreas(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea)

        self._last_user_chosen_expanded_height_in_pixels = (
            self.INITIAL_EXPANDED_HEIGHT_IN_PIXELS
        )

        self.output_log_widget.expansion_state_changed.connect(
            self._apply_size_constraints_for_expansion_state
        )
        self._apply_size_constraints_for_expansion_state(
            self.output_log_widget.is_expanded()
        )

    # ---- Sizing ----
    def _minimum_expanded_height_in_pixels(self) -> int:
        return (
            self.output_log_widget.header_height_in_pixels()
            + self.MINIMUM_EXPANDED_EXTRA_HEIGHT_IN_PIXELS
        )

    def _apply_size_constraints_for_expansion_state(self, is_expanded: bool) -> None:
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

        parent_main_window = self.parentWidget()
        if isinstance(parent_main_window, QtWidgets.QMainWindow):
            parent_main_window.resizeDocks(
                [self],
                [self._last_user_chosen_expanded_height_in_pixels],
                QtCore.Qt.Orientation.Vertical,
            )

    def resizeEvent(self, resize_event) -> None:
        super().resizeEvent(resize_event)
        # Remember the height only while expanded, ignoring transitional
        # sizes below the expanded minimum.
        if not self.output_log_widget.is_expanded():
            return
        current_height_in_pixels = self.height()
        if current_height_in_pixels >= self._minimum_expanded_height_in_pixels():
            self._last_user_chosen_expanded_height_in_pixels = current_height_in_pixels
