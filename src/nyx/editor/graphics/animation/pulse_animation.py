import typing

from PySide6 import QtCore, QtGui

from nyx.editor.graphics.animation.link_animation import LinkAnimation, color_from_config
from nyx.editor.utils.common import get_app_config

if typing.TYPE_CHECKING:
    from nyx.core.layered_config import NyxEditorLinkPulseAnimationConfigValues
    from nyx.editor.graphics.graphics_link import GraphicsLink


class PulseAnimation(LinkAnimation):
    """Dot with a short fading tail that travels from the source to the target.

    Looks and speed come from the link pulse animation config values, which are read
    once when the animation is created.

    Attributes:
        offset (float | None): distance of the dot from the source along the link,
            wrapped around the length of the link. None while the pulse is hidden.
    """

    def __init__(self, config: NyxEditorLinkPulseAnimationConfigValues | None = None):
        """Initialize PulseAnimation, hidden.

        Args:
            config (NyxEditorLinkPulseAnimationConfigValues | None): looks and speed of
                the pulse. The ones of the application config if omitted.
        """
        if config is None:
            config = get_app_config().values.editor_style.animations.link_pulse
        self.offset: float | None = None
        self.color = color_from_config(config)
        self.speed = float(config.speed)
        self.radius = max(float(config.radius), 0.0)
        self.tail_samples = max(int(config.tail_samples), 1)
        self.tail_step = float(config.tail_step)
        self.SHAPE_SIZE = self.radius * 2
        self.MARGIN = self.radius

    def advance(self, seconds: float):
        """Put the dot where it is at a point in time.

        Args:
            seconds (float): time since the animator started.
        """
        self.offset = seconds * self.speed

    def reset(self):
        """Hide the pulse."""
        self.offset = None

    def paint_above(self, painter: QtGui.QPainter, link: GraphicsLink):
        """Draw a dot at the offset followed by a fading tail.

        Args:
            painter (QtGui.QPainter): painter of the link.
            link (GraphicsLink): link being painted.
        """
        if self.offset is None or link.path_length <= 0:
            return

        path = link.path()
        head = self.offset % link.path_length
        color = QtGui.QColor(self.color)
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        for sample in range(self.tail_samples):
            distance = head - sample * self.tail_step
            if distance < 0:
                break
            fade = sample / self.tail_samples
            color.setAlphaF(1.0 - fade)
            painter.setBrush(color)
            radius = self.radius * (1.0 - 0.5 * fade)
            point = path.pointAtPercent(path.percentAtLength(distance))
            painter.drawEllipse(point, radius, radius)
        painter.restore()
