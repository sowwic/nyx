import collections.abc
import logging

from PySide6 import QtCore, QtGui

from nyx.core.layered_config import get_app_config
from nyx.static.enums import LinkStyle

LOGGER = logging.getLogger(__name__)

MIN_TANGENT = 40.0
"""Shortest handle of a bezier link, so links between close plugs still curve."""
SQUARE_HANDLE_WEIGHT = 0.5
"""Where the vertical part of a square link is, from the source (0) to the target (1)."""

PIN_SEARCH_SAMPLES = 32
"""Points taken along every part of a link to find the one closest to a new pin."""

_warned_styles: set[str] = set()


def build_bezier_path(start: QtCore.QPointF, end: QtCore.QPointF) -> QtGui.QPainterPath:
    """Build a smooth curve that leaves the start to the right and enters the end from
    the left.

    Args:
        start (QtCore.QPointF): scene position of the output socket.
        end (QtCore.QPointF): scene position of the input socket.

    Returns:
        QtGui.QPainterPath: path from the start to the end.
    """
    tangent = max(MIN_TANGENT, abs(end.x() - start.x()) * 0.5)
    path = QtGui.QPainterPath(start)
    path.cubicTo(
        start + QtCore.QPointF(tangent, 0.0),
        end - QtCore.QPointF(tangent, 0.0),
        end,
    )
    return path


def build_direct_path(start: QtCore.QPointF, end: QtCore.QPointF) -> QtGui.QPainterPath:
    """Build a straight line.

    Args:
        start (QtCore.QPointF): scene position of the output socket.
        end (QtCore.QPointF): scene position of the input socket.

    Returns:
        QtGui.QPainterPath: path from the start to the end.
    """
    path = QtGui.QPainterPath(start)
    path.lineTo(end)
    return path


def build_square_path(start: QtCore.QPointF, end: QtCore.QPointF) -> QtGui.QPainterPath:
    """Build a path of right angles: across, up or down, then across again.

    Args:
        start (QtCore.QPointF): scene position of the output socket.
        end (QtCore.QPointF): scene position of the input socket.

    Returns:
        QtGui.QPainterPath: path from the start to the end.
    """
    mid_x = start.x() + (end.x() - start.x()) * SQUARE_HANDLE_WEIGHT
    path = QtGui.QPainterPath(start)
    path.lineTo(mid_x, start.y())
    path.lineTo(mid_x, end.y())
    path.lineTo(end)
    return path


PATH_BUILDERS: dict[
    LinkStyle,
    collections.abc.Callable[[QtCore.QPointF, QtCore.QPointF], QtGui.QPainterPath],
] = {
    LinkStyle.BEZIER: build_bezier_path,
    LinkStyle.DIRECT: build_direct_path,
    LinkStyle.SQUARE: build_square_path,
}
"""Function that builds the path of every style."""


def build_link_path(
    style: LinkStyle,
    start: QtCore.QPointF,
    end: QtCore.QPointF,
    pins: collections.abc.Sequence[QtCore.QPointF] = (),
) -> QtGui.QPainterPath:
    """Build the path of a link in a style.

    Args:
        style (LinkStyle): style to draw the link in.
        start (QtCore.QPointF): scene position of the output socket.
        end (QtCore.QPointF): scene position of the input socket.
        pins (Sequence[QtCore.QPointF]): scene positions the path passes through, in
            order from the start. Every part between two points is drawn in the style.

    Returns:
        QtGui.QPainterPath: path from the start to the end.
    """
    builder = PATH_BUILDERS[style]
    points = [start, *pins, end]
    path = builder(points[0], points[1])
    for segment_start, segment_end in zip(points[1:-1], points[2:]):
        path.connectPath(builder(segment_start, segment_end))
    return path


def find_pin_index(
    style: LinkStyle,
    start: QtCore.QPointF,
    end: QtCore.QPointF,
    pins: collections.abc.Sequence[QtCore.QPointF],
    pos: QtCore.QPointF,
) -> int:
    """Find where a new pin at a position goes in the list of pins.

    Args:
        style (LinkStyle): style the link is drawn in.
        start (QtCore.QPointF): scene position of the output socket.
        end (QtCore.QPointF): scene position of the input socket.
        pins (Sequence[QtCore.QPointF]): current pins of the link.
        pos (QtCore.QPointF): scene position of the new pin.

    Returns:
        int: index to insert the pin at, so that it lands in the part of the link
            that passes closest to the position.
    """
    builder = PATH_BUILDERS[style]
    points = [start, *pins, end]
    best_index, best_distance = 0, float("inf")
    for index, (segment_start, segment_end) in enumerate(zip(points, points[1:])):
        segment = builder(segment_start, segment_end)
        for step in range(PIN_SEARCH_SAMPLES + 1):
            sample = segment.pointAtPercent(step / PIN_SEARCH_SAMPLES)
            distance = QtGui.QVector2D(sample - pos).lengthSquared()
            if distance < best_distance:
                best_index, best_distance = index, distance
    return best_index


def get_link_style() -> LinkStyle:
    """Get the style links are drawn in from the config.

    Returns:
        LinkStyle: style from the graphics stage config, the default one if the
            configured value is not a style. That is reported once per value.
    """
    value = get_app_config().values.editor_widgets.graphics_stage.link_style
    try:
        return LinkStyle(value)
    except ValueError:
        if value not in _warned_styles:
            _warned_styles.add(value)
            LOGGER.warning(
                f"Unknown link style {value!r}, using {LinkStyle.BEZIER.value!r}"
            )
        return LinkStyle.BEZIER
