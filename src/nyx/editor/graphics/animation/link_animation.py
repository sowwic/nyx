import abc
import logging
import typing

from PySide6 import QtGui

from nyx.editor.graphics.level_of_detail import LevelOfDetail

if typing.TYPE_CHECKING:
    from nyx.editor.graphics.graphics_link import GraphicsLink

LOGGER = logging.getLogger(__name__)


def color_from_config(config: typing.Any) -> QtGui.QColor:
    """Get the color of an animation config.

    Args:
        config (typing.Any): config values with a `color` text.

    Returns:
        QtGui.QColor: the color, the one of the default config values if the text is
            not a color.
    """
    color = QtGui.QColor(config.color)
    if not color.isValid():
        LOGGER.warning(f"Invalid animation color {config.color!r}, using the default")
        color = QtGui.QColor(type(config)().color)
    return color


class LinkAnimation(abc.ABC):
    """Visual effect of a graphics link that changes with time.

    There is one animation object per link and effect, it keeps the state of the
    effect. `LinkAnimator` moves it forward, the link calls the paint hooks while it
    paints itself. An animation only draws, it never decides when it runs.

    Attributes:
        SHAPE_SIZE (float): size in scene units of the smallest thing the animation
            draws, it is skipped where that is too small to see. Animations whose size
            comes from their config set it on the instance.
        MARGIN (float): room in scene units the animation needs around the stroke of the
            link. Set on the instance by animations whose size comes from their config.
    """

    SHAPE_SIZE = 10.0
    MARGIN = 0.0

    @abc.abstractmethod
    def advance(self, seconds: float):
        """Move the animation to a point in time.

        Args:
            seconds (float): time since the animator started. Not the time since the
                last call, so skipping calls does not make the animation fall behind.
        """

    @abc.abstractmethod
    def reset(self):
        """Hide the effect until the next `advance`."""

    def paint_below(self, painter: QtGui.QPainter, link: GraphicsLink):
        """Draw behind the stroke of the link. Draws nothing unless overridden.

        Args:
            painter (QtGui.QPainter): painter of the link.
            link (GraphicsLink): link being painted.
        """

    def paint_above(self, painter: QtGui.QPainter, link: GraphicsLink):
        """Draw over the stroke of the link. Draws nothing unless overridden.

        Args:
            painter (QtGui.QPainter): painter of the link.
            link (GraphicsLink): link being painted.
        """

    def is_visible_at(self, scale: float) -> bool:
        """Check whether the animation is big enough to see.

        Args:
            scale (float): scale of the link on screen.

        Returns:
            bool: the animation is worth drawing and advancing.
        """
        return LevelOfDetail.from_scale(scale, shape_size=self.SHAPE_SIZE).shows_shapes
