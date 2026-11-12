"""Painting helpers for the tests that look at what graphics items draw."""

import collections.abc

from PySide6 import QtCore, QtGui, QtWidgets


def _transparent_image(width: int, height: int) -> QtGui.QImage:
    image = QtGui.QImage(width, height, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    return image


def render_item(item: QtWidgets.QGraphicsItem, size: QtCore.QSizeF, scale=1.0):
    """Paint an item on a transparent image of `size` scene units, drawn at a scale.

    Args:
        item (QtWidgets.QGraphicsItem): item to paint.
        size (QtCore.QSizeF): size of the area to paint, in scene units.
        scale (float): scale the item is drawn with, as a view would.

    Returns:
        QtGui.QImage: what the item drew.
    """
    image = _transparent_image(
        int(size.width() * scale) + 1, int(size.height() * scale) + 1
    )
    painter = QtGui.QPainter(image)
    painter.scale(scale, scale)
    item.paint(painter, QtWidgets.QStyleOptionGraphicsItem(), None)
    painter.end()
    return image


def render_link(
    gr_link: QtWidgets.QGraphicsItem,
    draw: collections.abc.Callable[[QtGui.QPainter], None] | None = None,
    scale=1.0,
) -> QtGui.QImage:
    """Draw on a transparent image the size of a link's bounds, drawn at a scale.

    Args:
        gr_link (QtWidgets.QGraphicsItem): link whose bounds give the image.
        draw (Callable[[QtGui.QPainter], None] | None): draws with the painter, for
            example one animation of the link. The whole link is painted if omitted.
        scale (float): scale the link is drawn with, as a view would.

    Returns:
        QtGui.QImage: what was drawn.
    """
    rect = gr_link.boundingRect().toAlignedRect()
    image = _transparent_image(
        int(rect.width() * scale) + 1, int(rect.height() * scale) + 1
    )
    painter = QtGui.QPainter(image)
    painter.scale(scale, scale)
    painter.translate(-rect.topLeft())
    if draw is None:
        gr_link.paint(painter, QtWidgets.QStyleOptionGraphicsItem(), None)
    else:
        draw(painter)
    painter.end()
    return image


def opaque_pixels(image: QtGui.QImage, rect: QtCore.QRect | None = None) -> int:
    """Count the pixels that are not fully transparent.

    Args:
        image (QtGui.QImage): image to look at.
        rect (QtCore.QRect | None): part of the image to look at, all of it if omitted.

    Returns:
        int: number of pixels with an alpha above zero.
    """
    rect = image.rect() if rect is None else rect.intersected(image.rect())
    return sum(
        1
        for x in range(rect.left(), rect.right() + 1)
        for y in range(rect.top(), rect.bottom() + 1)
        if image.pixelColor(x, y).alpha() > 0
    )


def has_pixels(image: QtGui.QImage, rect: QtCore.QRect | None = None) -> bool:
    """Check whether anything was drawn, see `opaque_pixels`."""
    return opaque_pixels(image, rect) > 0


def peak_alpha(image: QtGui.QImage) -> int:
    """Get the highest alpha of the image."""
    return max(
        image.pixelColor(x, y).alpha()
        for x in range(image.width())
        for y in range(image.height())
    )


def has_color(image: QtGui.QImage, color: QtGui.QColor) -> bool:
    """Check whether a pixel has exactly a color, fully opaque."""
    rgb = color.rgb()
    return any(
        image.pixel(x, y) == rgb
        for x in range(image.width())
        for y in range(image.height())
    )
