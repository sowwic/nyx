from __future__ import annotations

import contextlib
import logging
import typing

from PySide6 import QtCore, QtWidgets

from nyx.utils import logging_fn

if typing.TYPE_CHECKING:
    from nyx.core.stage_crawler import StageCrawler


class ExecutionProgressDialog(QtWidgets.QDialog):
    """Modal dialog shown while a stage runs, with the latest log message and Cancel.

    It appears only if the run lasts longer than `SHOW_DELAY_MS`, so quick runs don't
    flash it. The crawler keeps it alive by processing events while it waits.
    """

    SHOW_DELAY_MS = 300
    MIN_LEVEL = logging.INFO

    def __init__(
        self, crawler: StageCrawler, parent: QtWidgets.QWidget | None = None
    ) -> None:
        """Initialize ExecutionProgressDialog.

        Args:
            crawler (StageCrawler): crawler whose run is shown, cancelled by the button.
            parent (QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._crawler = crawler
        self._full_message = "Starting..."
        self.setWindowTitle("Executing stage")
        self.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        self.setMinimumWidth(420)

        self._label = QtWidgets.QLabel(self)
        self._label.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored, QtWidgets.QSizePolicy.Policy.Preferred
        )
        self._progress_bar = QtWidgets.QProgressBar(self)
        self._progress_bar.setRange(0, 0)
        self._cancel_button = QtWidgets.QPushButton("Cancel", self)
        self._cancel_button.clicked.connect(self.cancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._label)
        layout.addWidget(self._progress_bar)
        layout.addWidget(
            self._cancel_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )

        self._show_timer = QtCore.QTimer(self)
        self._show_timer.setSingleShot(True)
        self._show_timer.setInterval(self.SHOW_DELAY_MS)
        self._show_timer.timeout.connect(self._show_now)
        self._set_label_text(self._full_message)

    @property
    def message(self) -> str:
        """str: latest message, not elided."""
        return self._full_message

    def _set_label_text(self, text: str) -> None:
        """Show a message on one line, elided to the width of the label.

        Args:
            text (str): message.
        """
        self._full_message = text
        self._label.setToolTip(text)
        elided = self._label.fontMetrics().elidedText(
            text, QtCore.Qt.TextElideMode.ElideRight, max(self._label.width(), 380)
        )
        self._label.setText(elided)

    def on_record_logged(self, record: logging.LogRecord) -> None:
        """Show a log record as the progress message, if it is important enough.

        Args:
            record (logging.LogRecord): logged record.
        """
        if record.levelno < self.MIN_LEVEL or self._crawler.is_cancel_requested:
            return
        self._set_label_text(logging_fn.format_log_record_message_as_single_line(record))

    def cancel(self) -> None:
        """Ask the run to stop."""
        self._crawler.request_cancel()
        self._cancel_button.setEnabled(False)
        self._set_label_text("Cancelling...")

    def reject(self) -> None:
        """Escape and the close button cancel the run instead of closing the dialog."""
        if self._cancel_button.isEnabled():
            self.cancel()

    def _show_now(self) -> None:
        """Show the dialog and let the user click it."""
        self._crawler.accept_user_input = True
        self.show()

    @contextlib.contextmanager
    def watching(self) -> typing.Iterator[ExecutionProgressDialog]:
        """Context in which the dialog follows the log and shows up if it takes long."""
        handler = logging_fn.add_signal_handler(logging.getLogger())
        handler.emitter.record_logged.connect(self.on_record_logged)
        self._show_timer.start()
        try:
            yield self
        finally:
            self._show_timer.stop()
            handler.emitter.record_logged.disconnect(self.on_record_logged)
            self.hide()
