import collections.abc
import typing

from PySide6 import QtCore

if typing.TYPE_CHECKING:
    from nyx.editor.graphics.graphics_link import GraphicsLink


class LinkPulseAnimator(QtCore.QObject):
    """Drives the pulse of the links on the execution chain with a single timer.

    The timer only runs while there are links to animate and the animator is not
    paused. A tick moves the pulse of every registered link that is in view by the time
    passed, so the cost is proportional to the number of pulsing links on screen and
    nothing is computed while painting. Ticks do nothing while nothing shows the links.
    """

    INTERVAL_MS = 33

    def __init__(
        self,
        is_visible: collections.abc.Callable[[], bool] | None = None,
        visible_rects: collections.abc.Callable[[], list[QtCore.QRectF]] | None = None,
        parent: QtCore.QObject | None = None,
    ):
        """Initialize LinkPulseAnimator.

        Args:
            is_visible (Callable[[], bool] | None): tells whether anything shows the
                links, ticks are skipped while it returns False. Always visible if
                omitted.
            visible_rects (Callable[[], list[QRectF]] | None): scene areas the links
                are shown in. Links outside of all of them are not animated, none are
                if it returns an empty list. Links are animated wherever they are if
                omitted.
            parent (QtCore.QObject | None): parent object.
        """
        super().__init__(parent)
        self._is_visible = is_visible
        self._visible_rects = visible_rects
        self._links: set[GraphicsLink] = set()
        self._paused = False
        self._clock = QtCore.QElapsedTimer()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self.INTERVAL_MS)
        self._timer.timeout.connect(self._on_timeout)

    @property
    def links(self) -> frozenset[GraphicsLink]:
        """frozenset[GraphicsLink]: links being animated."""
        return frozenset(self._links)

    @property
    def is_running(self) -> bool:
        """bool: the timer is running."""
        return self._timer.isActive()

    @property
    def is_paused(self) -> bool:
        """bool: the animation is paused, the pulses are hidden."""
        return self._paused

    @property
    def is_animating(self) -> bool:
        """bool: ticks move the pulses of at least one link that is in view.

        The timer also runs while nothing shows the pulses, for example when the view
        is zoomed too far out or looks somewhere else, but its ticks are skipped then.
        """
        return self.is_running and bool(self.links_in_view())

    def links_in_view(self) -> list[GraphicsLink]:
        """Find the links whose pulse is worth moving.

        Returns:
            list[GraphicsLink]: registered links in an area that is shown. Empty
                while nothing shows the links.
        """
        if not self._is_scene_visible():
            return []
        if self._visible_rects is None:
            return list(self._links)
        rects = self._visible_rects()
        return [
            link
            for link in self._links
            if any(link.sceneBoundingRect().intersects(rect) for rect in rects)
        ]

    def register(self, link: GraphicsLink):
        """Animate a link.

        Args:
            link (GraphicsLink): pulsing link.
        """
        self._links.add(link)
        self._sync_timer()

    def unregister(self, link: GraphicsLink):
        """Stop animating a link and hide its pulse.

        Args:
            link (GraphicsLink): link to release.
        """
        if link not in self._links:
            return
        self._links.discard(link)
        link.set_pulse_offset(None)
        self._sync_timer()

    def clear(self):
        """Stop animating all links."""
        for link in list(self._links):
            self.unregister(link)

    def set_paused(self, paused: bool):
        """Pause or resume the animation. Pulses are hidden while paused.

        Args:
            paused (bool): pause the animation.
        """
        if paused == self._paused:
            return
        self._paused = paused
        if paused:
            for link in self._links:
                link.set_pulse_offset(None)
        self._sync_timer()

    def tick(self, elapsed_ms: int):
        """Move the pulses.

        Args:
            elapsed_ms (int): milliseconds since the animation started.
        """
        if self._paused or not self._is_scene_visible():
            return
        seconds = elapsed_ms / 1000.0
        for link in self.links_in_view():
            link.set_pulse_offset(seconds * link.PULSE_SPEED)

    def _is_scene_visible(self) -> bool:
        """bool: something shows the links."""
        return self._is_visible is None or self._is_visible()

    def _sync_timer(self):
        """Run the timer only when there is something to animate."""
        should_run = bool(self._links) and not self._paused
        if should_run and not self._timer.isActive():
            self._clock.start()
            self._timer.start()
        elif not should_run and self._timer.isActive():
            self._timer.stop()

    def _on_timeout(self):
        """Tick with the time since the timer started."""
        self.tick(self._clock.elapsed())
