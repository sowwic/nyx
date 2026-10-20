import collections.abc
import typing

from PySide6 import QtCore

if typing.TYPE_CHECKING:
    from nyx.editor.graphics.graphics_link import GraphicsLink
    from nyx.editor.graphics.animation.link_animation import LinkAnimation


class ViewArea(typing.NamedTuple):
    """Part of the scene a view shows.

    Attributes:
        rect (QtCore.QRectF): area in scene coordinates.
        scale (float): scale the view shows the scene with.
    """

    rect: QtCore.QRectF
    scale: float


class LinkAnimator(QtCore.QObject):
    """Drives the animations of graphics links with a single timer.

    Animations are registered per link and kind (a `LinkAnimation` class). The timer
    only runs while there are animations and the animator is not paused. A tick moves
    the animations that are in view by the time passed, so the cost is proportional to
    the number of animated links on screen and nothing is computed while painting.
    Ticks do nothing while nothing shows the links.
    """

    INTERVAL_MS = 33

    def __init__(
        self,
        visible_areas: collections.abc.Callable[[], list[ViewArea]] | None = None,
        parent: QtCore.QObject | None = None,
    ):
        """Initialize LinkAnimator.

        Args:
            visible_areas (Callable[[], list[ViewArea]] | None): parts of the scene
                that are shown. An animation only runs in an area where it is big
                enough to see, none run if it returns an empty list. Animations run
                wherever the links are if omitted.
            parent (QtCore.QObject | None): parent object.
        """
        super().__init__(parent)
        self._visible_areas = visible_areas
        self._animations: dict[GraphicsLink, dict[type, LinkAnimation]] = {}
        self._paused = False
        self._clock = QtCore.QElapsedTimer()
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self.INTERVAL_MS)
        self._timer.timeout.connect(self._on_timeout)

    @property
    def links(self) -> frozenset[GraphicsLink]:
        """frozenset[GraphicsLink]: links that have an animation."""
        return frozenset(self._animations)

    @property
    def is_running(self) -> bool:
        """bool: the timer is running."""
        return self._timer.isActive()

    @property
    def is_paused(self) -> bool:
        """bool: the animations are paused and hidden."""
        return self._paused

    @property
    def is_animating(self) -> bool:
        """bool: ticks move at least one animation that is in view.

        The timer also runs while nothing shows the animations, for example when the
        view is zoomed too far out or looks somewhere else, but its ticks are skipped.
        """
        return self.is_running and bool(self.active_links())

    def animations_of(self, link: GraphicsLink) -> list[LinkAnimation]:
        """Get the animations registered for a link.

        Args:
            link (GraphicsLink): link to look up.

        Returns:
            list[LinkAnimation]: animations of the link, empty for an unknown one.
        """
        return list(self._animations.get(link, {}).values())

    def active_links(self) -> list[GraphicsLink]:
        """Find the links with an animation that is worth moving.

        Returns:
            list[GraphicsLink]: links with an animation in view.
        """
        return list({link for link, _animation in self._animations_in_view()})

    def register(self, link: GraphicsLink, animation: LinkAnimation):
        """Animate a link. An animation of the same kind is replaced.

        Args:
            link (GraphicsLink): link to animate.
            animation (LinkAnimation): animation to run.
        """
        kind = type(animation)
        if kind in self._animations.get(link, {}):
            self._remove(link, kind)
        self._animations.setdefault(link, {})[kind] = animation
        link.add_animation(animation)
        self._sync_timer()

    def unregister(self, link: GraphicsLink, kind: type | None = None):
        """Stop animating a link and hide its animations.

        Args:
            link (GraphicsLink): link to release.
            kind (type | None): kind of animation to stop, all of the link if omitted.
        """
        for registered_kind in list(self._animations.get(link, {})):
            if kind is None or registered_kind is kind:
                self._remove(link, registered_kind)
        self._sync_timer()

    def clear(self, kind: type | None = None):
        """Stop animating links.

        Args:
            kind (type | None): kind of animation to stop, all if omitted.
        """
        for link in list(self._animations):
            self.unregister(link, kind)

    def set_paused(self, paused: bool):
        """Pause or resume the animations. They are hidden while paused.

        Args:
            paused (bool): pause the animations.
        """
        if paused == self._paused:
            return
        self._paused = paused
        if paused:
            for link, animation in self._all_animations():
                animation.reset()
                link.update()
        self._sync_timer()

    def tick(self, elapsed_ms: int):
        """Move the animations that are in view.

        Args:
            elapsed_ms (int): milliseconds since the animator started.
        """
        if self._paused:
            return
        seconds = elapsed_ms / 1000.0
        moved: set[GraphicsLink] = set()
        for link, animation in self._animations_in_view():
            animation.advance(seconds)
            moved.add(link)
        for link in moved:
            link.update()

    def _remove(self, link: GraphicsLink, kind: type):
        """Forget an animation of a link and take it off the link.

        Args:
            link (GraphicsLink): link of the animation.
            kind (type): kind of the animation.
        """
        animations = self._animations[link]
        animations.pop(kind).reset()
        link.remove_animation(kind)
        if not animations:
            del self._animations[link]

    def _all_animations(self) -> list[tuple[GraphicsLink, LinkAnimation]]:
        """list[tuple[GraphicsLink, LinkAnimation]]: every registered animation."""
        return [
            (link, animation)
            for link, animations in self._animations.items()
            for animation in animations.values()
        ]

    def _animations_in_view(self) -> list[tuple[GraphicsLink, LinkAnimation]]:
        """Find the animations that are on screen and big enough to see.

        Returns:
            list[tuple[GraphicsLink, LinkAnimation]]: link and animation pairs. Empty
                while nothing shows the links.
        """
        if self._visible_areas is None:
            return self._all_animations()
        areas = self._visible_areas()
        if not areas:
            return []

        found = []
        for link, animations in self._animations.items():
            bounds = link.sceneBoundingRect()
            scales = [area.scale for area in areas if bounds.intersects(area.rect)]
            if not scales:
                continue
            found.extend(
                (link, animation)
                for animation in animations.values()
                if any(animation.is_visible_at(scale) for scale in scales)
            )
        return found

    def _sync_timer(self):
        """Run the timer only when there is something to animate."""
        should_run = bool(self._animations) and not self._paused
        if should_run and not self._timer.isActive():
            self._clock.start()
            self._timer.start()
        elif not should_run and self._timer.isActive():
            self._timer.stop()

    def _on_timeout(self):
        """Tick with the time since the timer started."""
        self.tick(self._clock.elapsed())
