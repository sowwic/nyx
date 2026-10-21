import logging
import math
import typing

from PySide6 import QtCore, QtGui

from nyx.editor.graphics.animation.link_animation import LinkAnimation, color_from_config
from nyx.editor.utils.common import get_app_config

if typing.TYPE_CHECKING:
    from nyx.core.config_values.animation_values import (
        NyxEditorLinkGlowAnimationConfigValues,
    )
    from nyx.editor.graphics.graphics_link import GraphicsLink

LOGGER = logging.getLogger(__name__)

MIN_PERIOD = 0.05
"""Shortest period in seconds, so a bad config value can not stop the glow."""


class GlowAnimation(LinkAnimation):
    """Halo behind the stroke of a link, whose strength swells and fades.

    Looks and speed come from the link glow animation config values, which are read
    once when the animation is created.

    Attributes:
        intensity (float | None): strength of the glow from 0 (none) to 1 (full). None
            while the glow is hidden.
    """

    def __init__(self, config: NyxEditorLinkGlowAnimationConfigValues | None = None):
        """Initialize GlowAnimation, hidden.

        Args:
            config (NyxEditorLinkGlowAnimationConfigValues | None): looks and speed of
                the glow. The ones of the application config if omitted.
        """
        if config is None:
            config = get_app_config().values.editor_style.animations.link_glow
        self.intensity: float | None = None
        self.color = color_from_config(config)
        self.period = max(float(config.period), MIN_PERIOD)
        self.layers = self._parse_layers(config.layers)
        widest = self.layers[0][0] if self.layers else 0.0
        self.SHAPE_SIZE = widest
        self.MARGIN = widest / 2

    @staticmethod
    def _parse_layers(layers: typing.Iterable) -> list[tuple[float, float]]:
        """Read the layers of the config, leaving out the ones that are not usable.

        Args:
            layers (typing.Iterable): (width, opacity) pairs. Config files give lists.

        Returns:
            list[tuple[float, float]]: pairs with a width above zero and the opacity
                limited to 0-1, from the widest to the narrowest.
        """
        parsed = []
        for layer in layers:
            try:
                width, opacity = (float(value) for value in layer)
            except (TypeError, ValueError):
                LOGGER.warning(f"Ignoring invalid glow layer {layer!r}")
                continue
            if width > 0:
                parsed.append((width, min(max(opacity, 0.0), 1.0)))
        return sorted(parsed, reverse=True)

    def advance(self, seconds: float):
        """Set the strength of the glow at a point in time.

        It starts at 0, swells to 1 half a period later and fades out again.

        Args:
            seconds (float): time since the animator started.
        """
        self.intensity = 0.5 - 0.5 * math.cos(2 * math.pi * seconds / self.period)

    def reset(self):
        """Hide the glow."""
        self.intensity = None

    def paint_below(self, painter: QtGui.QPainter, link: GraphicsLink):
        """Draw the halo: wide translucent strokes along the link.

        Args:
            painter (QtGui.QPainter): painter of the link.
            link (GraphicsLink): link being painted.
        """
        if not self.intensity or not self.layers:
            return

        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        path = link.path()
        color = QtGui.QColor(self.color)
        for width, opacity in self.layers:
            color.setAlphaF(opacity * self.intensity)
            pen = QtGui.QPen(color, width)
            pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawPath(path)
        painter.restore()
