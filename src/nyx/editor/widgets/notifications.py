from __future__ import annotations

import typing

from PySide6 import QtCore, QtGui, QtWidgets


class NotificationMessage(QtWidgets.QFrame):
    """One notification: an optional icon, a text and a button to dismiss it.

    It fades out after `fade` seconds, or stays until it is dismissed.
    """

    FADE_IN_MS = 150
    FADE_OUT_MS = 400
    MAX_TEXT_WIDTH = 440
    MIN_WIDTH = 320
    ICON_SIZE = 32

    closed = QtCore.Signal(object)
    """Emitted with the message when it is gone."""

    def __init__(
        self,
        text: str,
        fade: float | None = None,
        icon: str | QtGui.QIcon | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Initialize NotificationMessage.

        Args:
            text (str): message text.
            fade (float | None): seconds until it fades out, None or 0 to keep it.
            icon (str | QIcon | None): icon or resource path of one.
            parent (QWidget | None): widget the message is shown over.
        """
        super().__init__(parent)
        self._is_closing = False
        self.setObjectName("NotificationMessage")
        self.setStyleSheet(
            "#NotificationMessage { background-color: #2b2b2b; border: 1px solid #555;"
            " border-radius: 8px; } #NotificationMessage QLabel { color: #eeeeee; }"
        )
        self._opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 10, 14)
        layout.setSpacing(12)
        self._icon_label = QtWidgets.QLabel(self)
        qicon = QtGui.QIcon(icon) if isinstance(icon, str) else icon
        if qicon is not None and not qicon.isNull():
            self._icon_label.setPixmap(qicon.pixmap(self.ICON_SIZE, self.ICON_SIZE))
            layout.addWidget(
                self._icon_label, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter
            )
        self._text_label = QtWidgets.QLabel(text, self)
        self._text_label.setWordWrap(True)
        text_font = self._text_label.font()
        text_font.setPointSizeF(text_font.pointSizeF() * 1.35)
        self._text_label.setFont(text_font)
        self._text_label.setMaximumWidth(self.MAX_TEXT_WIDTH)
        layout.addWidget(self._text_label, stretch=1)
        self.dismiss_button = QtWidgets.QToolButton(self)
        self.dismiss_button.setText("✕")
        self.dismiss_button.setAutoRaise(True)
        self.dismiss_button.setToolTip("Dismiss")
        self.dismiss_button.setFixedSize(24, 24)
        self.dismiss_button.setStyleSheet(
            "QToolButton { color: #aaaaaa; border: none; font-size: 14px; }"
            "QToolButton:hover { color: #ffffff; }"
        )
        self.dismiss_button.clicked.connect(self.dismiss)
        layout.addWidget(self.dismiss_button, alignment=QtCore.Qt.AlignmentFlag.AlignTop)

        self._animation = QtCore.QPropertyAnimation(
            self._opacity_effect, b"opacity", self
        )
        self._on_animation_finished: typing.Callable[[], None] | None = None
        self._animation.finished.connect(self._handle_animation_finished)
        self._fade_timer = QtCore.QTimer(self)
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self.dismiss)
        if fade and fade > 0:
            self._fade_timer.setInterval(int(fade * 1000))
        self.setMinimumWidth(self.MIN_WIDTH)
        self.adjustSize()

    @property
    def text(self) -> str:
        """str: message text."""
        return self._text_label.text()

    @property
    def is_closing(self) -> bool:
        """bool: the message is fading out or gone."""
        return self._is_closing

    def appear(self) -> None:
        """Show the message with a fade in and start its timer, if it has one."""
        self.show()
        self.raise_()
        self._animate(1.0, self.FADE_IN_MS)
        if self._fade_timer.interval() > 0:
            self._fade_timer.start()

    def dismiss(self) -> None:
        """Fade the message out and remove it. Does nothing when already doing so."""
        if self._is_closing:
            return
        self._is_closing = True
        self._fade_timer.stop()
        self._animate(0.0, self.FADE_OUT_MS, on_finished=self._finish)

    def _animate(
        self,
        target: float,
        duration_ms: int,
        on_finished: typing.Callable[[], None] | None = None,
    ) -> None:
        """Animate the opacity.

        Args:
            target (float): opacity to reach.
            duration_ms (int): duration.
            on_finished (Callable | None): called when the animation is done.
        """
        self._animation.stop()
        self._on_animation_finished = on_finished
        self._animation.setDuration(duration_ms)
        self._animation.setStartValue(self._opacity_effect.opacity())
        self._animation.setEndValue(target)
        self._animation.start()

    def _handle_animation_finished(self) -> None:
        """Run what was to follow the animation."""
        if self._on_animation_finished is not None:
            self._on_animation_finished()

    def _finish(self) -> None:
        """Remove the message."""
        self.hide()
        self.closed.emit(self)
        self.deleteLater()


class NotificationManager(QtCore.QObject):
    """Shows notification messages in the bottom right corner of the editor window.

    Used through its class methods, there is nothing to create:
    `NotificationManager.add_message("Saved", fade=5)`. Until a window is set with
    `set_host` (the CLI, tests) messages are ignored.
    """

    MARGIN = 24
    SPACING = 12

    _instance: NotificationManager | None = None
    _requested = QtCore.Signal(str, float, object)

    def __init__(self, host: QtWidgets.QWidget) -> None:
        """Initialize NotificationManager. Use `set_host` instead of creating one.

        Args:
            host (QWidget): window the messages are shown over.
        """
        super().__init__(host)
        self._host = host
        self._messages: list[NotificationMessage] = []
        host.installEventFilter(self)
        self._requested.connect(self._add_message)

    @classmethod
    def set_host(cls, host: QtWidgets.QWidget | None) -> None:
        """Set the window messages are shown over, None to stop showing them.

        Args:
            host (QWidget | None): window.
        """
        if cls._instance is not None:
            cls._instance.deleteLater()
            cls._instance = None
        if host is not None:
            cls._instance = cls(host)

    @classmethod
    def add_message(
        cls,
        text: str,
        fade: float | None = None,
        icon: str | QtGui.QIcon | None = None,
    ) -> NotificationMessage | None:
        """Show a message.

        Args:
            text (str): message text.
            fade (float | None): seconds until it fades out, None or 0 to keep it
                until it is dismissed.
            icon (str | QIcon | None): icon or resource path of one.

        Returns:
            NotificationMessage | None: the message, None if it can't be shown right
                now: there is no window, or this is not the GUI thread, then it is
                shown as soon as that thread gets to it.
        """
        manager = cls._instance
        if manager is None:
            return None
        if QtCore.QThread.currentThread() is not manager.thread():
            manager._requested.emit(text, float(fade or 0), icon)
            return None
        return manager._add_message(text, fade, icon)

    @classmethod
    def clear(cls) -> None:
        """Dismiss every message."""
        if cls._instance is not None:
            for message in list(cls._instance._messages):
                message.dismiss()

    @property
    def messages(self) -> list[NotificationMessage]:
        """list[NotificationMessage]: messages shown, oldest first."""
        return list(self._messages)

    def _add_message(
        self, text: str, fade: float | None, icon: str | QtGui.QIcon | None
    ) -> NotificationMessage:
        """Create a message and show it below the ones shown already."""
        message = NotificationMessage(text, fade=fade, icon=icon, parent=self._host)
        message.closed.connect(self._on_message_closed)
        self._messages.append(message)
        self._layout_messages()
        message.appear()
        return message

    def _on_message_closed(self, message: NotificationMessage) -> None:
        """Forget a message and close the gap it left."""
        if message in self._messages:
            self._messages.remove(message)
        self._layout_messages()

    def _layout_messages(self) -> None:
        """Stack the messages upwards from the bottom right corner of the window."""
        bottom = self._host.height() - self.MARGIN
        for message in reversed(self._messages):
            message.adjustSize()
            bottom -= message.height()
            message.move(self._host.width() - self.MARGIN - message.width(), bottom)
            bottom -= self.SPACING

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Keep the messages in the corner when the window changes size.

        Args:
            watched (QObject): watched object.
            event (QEvent): event.

        Returns:
            bool: always False, events are not consumed.
        """
        if watched is self._host and event.type() == QtCore.QEvent.Type.Resize:
            self._layout_messages()
        return False
