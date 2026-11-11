import logging

from PySide6 import QtCore, QtGui, QtWidgets

from nyx.utils.logging_fn import QSignalHandler
from nyx.version import __version__


class NyxStartupSplash(QtWidgets.QSplashScreen):
    """Splash screen showing the log messages logged while the editor starts.

    The layout is in device independent pixels of the background, which is shown at
    `SIZE`.
    """

    SIZE = QtCore.QSize(640, 400)
    SUBTITLE_TEXT = "Python nodal execution graph"
    VERSION_TEXT = f"v{__version__}"
    TITLE_COLOR = QtGui.QColor(232, 230, 223)
    SECONDARY_COLOR = QtGui.QColor(143, 149, 168)
    LOGO_RECT = QtCore.QRect(64, 135, 128, 128)
    TEXT_LEFT = 216
    TITLE_RECT = QtCore.QRect(TEXT_LEFT, 146, 400, 64)
    TITLE_PIXEL_SIZE = 40
    SUBTITLE_RECT = QtCore.QRect(TEXT_LEFT, 204, 400, 28)
    SUBTITLE_PIXEL_SIZE = 16
    FOOTER_RECT = QtCore.QRect(64, 346, 512, 24)
    FOOTER_PIXEL_SIZE = 13
    FOOTER_GAP = 16  # Space kept between the message and the version.
    BACKGROUND_PIXMAP_SOURCE = ":/images/splash_background"
    APP_ICON_SOURCE = ":/icons/nyx/1024"

    def __init__(self, screen: QtGui.QScreen | None = None) -> None:
        """Initialize NyxStartupSplash.

        Args:
            screen (QtGui.QScreen | None): screen to appear on, primary if None.
        """
        super().__init__(screen, self._create_background_pixmap())
        self._signal_handler: QSignalHandler | None = None
        self.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint)

    @classmethod
    def _create_background_pixmap(cls) -> QtGui.QPixmap:
        """Draw the logo, application name, subtitle and version on the background.

        Returns:
            QtGui.QPixmap: splash pixmap of `SIZE` device independent pixels, with
                the resolution of the background so it stays sharp on high DPI.
        """
        pixmap = QtGui.QPixmap(cls.BACKGROUND_PIXMAP_SOURCE)
        pixmap.setDevicePixelRatio(pixmap.width() / cls.SIZE.width())

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHints(
            QtGui.QPainter.RenderHint.Antialiasing
            | QtGui.QPainter.RenderHint.SmoothPixmapTransform
            | QtGui.QPainter.RenderHint.TextAntialiasing
        )
        painter.drawPixmap(cls.LOGO_RECT, QtGui.QPixmap(cls.APP_ICON_SOURCE))

        painter.setFont(cls._font(cls.TITLE_PIXEL_SIZE, bold=True))
        painter.setPen(cls.TITLE_COLOR)
        painter.drawText(
            cls.TITLE_RECT,
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            f"[{QtWidgets.QApplication.applicationDisplayName()}]",
        )

        painter.setFont(cls._font(cls.SUBTITLE_PIXEL_SIZE))
        painter.setPen(cls.SECONDARY_COLOR)
        painter.drawText(
            cls.SUBTITLE_RECT,
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            cls.SUBTITLE_TEXT,
        )

        painter.setFont(cls._font(cls.FOOTER_PIXEL_SIZE))
        painter.drawText(
            cls.FOOTER_RECT,
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter,
            cls.VERSION_TEXT,
        )
        painter.end()
        return pixmap

    @staticmethod
    def _font(pixel_size: int, bold: bool = False) -> QtGui.QFont:
        """Create a splash font.

        Args:
            pixel_size (int): font size in device independent pixels.
            bold (bool): use a bold weight.

        Returns:
            QtGui.QFont: application font with the size and weight.
        """
        font = QtGui.QFont(QtWidgets.QApplication.font())
        font.setPixelSize(pixel_size)
        font.setBold(bold)
        return font

    def connect_to_logger(self, signal_handler: QSignalHandler) -> None:
        """Show the records of a logger signal handler as the splash message.

        Args:
            signal_handler (QSignalHandler): handler to listen to.
        """
        self.disconnect_from_logger()
        self._signal_handler = signal_handler
        signal_handler.emitter.record_logged.connect(self._on_record_logged)

    def disconnect_from_logger(self) -> None:
        """Stop showing log records."""
        if self._signal_handler is None:
            return
        self._signal_handler.emitter.record_logged.disconnect(self._on_record_logged)
        self._signal_handler = None

    def show_log_message(self, message: str) -> None:
        """Show a message in the footer.

        Args:
            message (str): text to show.
        """
        self.showMessage(message.splitlines()[0] if message else "")
        # Startup blocks the event loop, the message is only painted when it spins.
        QtWidgets.QApplication.processEvents()

    def drawContents(self, painter: QtGui.QPainter) -> None:
        """Draw the message at the left of the footer, elided to leave the version.

        Args:
            painter (QtGui.QPainter): painter of the splash.
        """
        font = self._font(self.FOOTER_PIXEL_SIZE)
        metrics = QtGui.QFontMetrics(font)
        available_width = (
            self.FOOTER_RECT.width()
            - metrics.horizontalAdvance(self.VERSION_TEXT)
            - self.FOOTER_GAP
        )
        painter.setFont(font)
        painter.setPen(self.SECONDARY_COLOR)
        painter.drawText(
            self.FOOTER_RECT,
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
            metrics.elidedText(
                self.message(), QtCore.Qt.TextElideMode.ElideRight, available_width
            ),
        )

    def finish(self, main_window: QtWidgets.QWidget) -> None:
        """Close the splash once the main window is shown.

        Args:
            main_window (QtWidgets.QWidget): window that replaces the splash.
        """
        self.disconnect_from_logger()
        super().finish(main_window)

    def _on_record_logged(self, record: logging.LogRecord) -> None:
        """Show the message of a record.

        Args:
            record (logging.LogRecord): logged record.
        """
        self.show_log_message(record.getMessage())
