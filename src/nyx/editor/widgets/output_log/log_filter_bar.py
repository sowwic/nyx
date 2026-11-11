import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QToolButton,
    QWidget,
)

SEARCH_FIELD_MAX_WIDTH = 300

LEVEL_CHOICES: tuple[tuple[str, int], ...] = (
    ("Debug", logging.DEBUG),
    ("Info", logging.INFO),
    ("Warning", logging.WARNING),
    ("Error", logging.ERROR),
)


class LogFilterBar(QWidget):
    """Search field and minimum level selector.

    Attributes:
        search_text_changed: emitted with the new search text
        minimum_level_changed: emitted with the new minimum logging level
        clear_requested: emitted when Clear Log is chosen in the settings menu
    """

    search_text_changed = Signal(str)
    minimum_level_changed = Signal(int)
    clear_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        """Initialize LogFilterBar.

        Args:
            parent (QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._create_actions()
        self._create_widgets()
        self._create_layouts()
        self._create_connections()

    def _create_actions(self) -> None:
        """Create actions."""
        self._clear_log_action = QAction(
            QIcon(":/icons/delete_entries"), "Clear Log", self
        )

    def _create_widgets(self) -> None:
        """Create child widgets."""
        self._settings_menu = QMenu(self)
        self._settings_menu.addAction(self._clear_log_action)

        self._settings_button = QToolButton(self)
        self._settings_button.setAutoRaise(True)
        self._settings_button.setIcon(QIcon(":/icons/settings"))
        self._settings_button.setText("Settings")
        self._settings_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self._settings_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._settings_button.setMenu(self._settings_menu)

        self._search_field = QLineEdit(self)
        self._search_field.setPlaceholderText("Search")
        self._search_field.setClearButtonEnabled(True)
        self._search_field.setMaximumWidth(SEARCH_FIELD_MAX_WIDTH)

        self._level_combo_box = QComboBox(self)
        for label, level in LEVEL_CHOICES:
            self._level_combo_box.addItem(label, level)
        self._level_combo_box.setToolTip("Minimum level")

    def _create_layouts(self) -> None:
        """Create layouts."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)
        main_layout.addWidget(self._search_field)
        main_layout.addWidget(self._level_combo_box)
        main_layout.addStretch(1)
        main_layout.addWidget(self._settings_button)

    def _create_connections(self) -> None:
        """Create signal-slot connections."""
        self._clear_log_action.triggered.connect(self.clear_requested)
        self._search_field.textChanged.connect(self.search_text_changed)
        self._level_combo_box.currentIndexChanged.connect(self._on_level_index_changed)

    def get_minimum_level(self) -> int:
        """int: selected minimum logging level."""
        return self._level_combo_box.currentData()

    def set_minimum_level(self, minimum_level: int) -> None:
        """Select a minimum level, falling back to the first choice if unknown.

        Args:
            minimum_level (int): logging level number.
        """
        index = self._level_combo_box.findData(minimum_level)
        self._level_combo_box.setCurrentIndex(max(index, 0))

    def _on_level_index_changed(self, index: int) -> None:
        """Emit the level of the selected item."""
        self.minimum_level_changed.emit(self._level_combo_box.itemData(index))
