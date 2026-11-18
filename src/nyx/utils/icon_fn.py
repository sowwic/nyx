"""Icons made from image files, to match the monochrome icons of the editor."""

import pathlib

from PySide6 import QtCore, QtGui

ICON_SIZE = 24
"""Pixel size of the icons of the editor."""
# The glyph of an icon of the editor is pure white, the shape is all in the alpha.
ICON_COLOR = QtGui.QColor(255, 255, 255)


def _load_image(path: pathlib.Path | str, size: int) -> QtGui.QImage:
    """Read an image file, vector formats drawn at the size they are needed at.

    Args:
        path (pathlib.Path | str): image file or resource path (`:/icons/...`).
        size (int): pixel size the image is going to be shown at.

    Raises:
        FileNotFoundError: the file doesn't exist.
        ValueError: the file is not an image that can be read.

    Returns:
        QtGui.QImage: the image, at most `size` pixels on each side.
    """
    text = str(path)
    if not text.startswith(":") and not pathlib.Path(text).is_file():
        raise FileNotFoundError(f"Image file not found: {text}")
    image = QtGui.QIcon(text).pixmap(QtCore.QSize(size, size)).toImage()
    if image.isNull():
        raise ValueError(f"Can't read an image from {text}")
    return image


def _has_transparency(image: QtGui.QImage) -> bool:
    """Check if any pixel of an image is not fully opaque."""
    if not image.hasAlphaChannel():
        return False
    return any(
        image.pixelColor(x, y).alpha() < 255
        for y in range(image.height())
        for x in range(image.width())
    )


def create_mono_image(
    path: pathlib.Path | str,
    size: int = ICON_SIZE,
    color: QtGui.QColor | QtCore.Qt.GlobalColor = ICON_COLOR,
    invert: bool = False,
) -> QtGui.QImage:
    """Make a one color image of the shape in an image file.

    The shape is found from the transparency of the image. An image without any, like a
    black drawing on white, gets it from the brightness instead: the dark parts are the
    shape, or the light parts with `invert`. The result is scaled to fit a square of
    `size` pixels, keeping the proportions, and centered in it.

    Args:
        path (pathlib.Path | str): image file or resource path (`:/icons/...`).
        size (int): pixel size of the square image.
        color (QtGui.QColor | Qt.GlobalColor): color of the shape, white like the icons
            of the editor by default. Use an opaque color.
        invert (bool): light parts are the shape. Only for an image with no
            transparency.

    Raises:
        FileNotFoundError: the file doesn't exist.
        ValueError: the file is not an image that can be read.

    Returns:
        QtGui.QImage: square image of the color, shaped by the alpha channel.
    """
    source = _load_image(path, size)
    by_alpha = _has_transparency(source)
    source = source.scaled(
        size,
        size,
        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )
    x, y = (size - source.width()) // 2, (size - source.height()) // 2

    # Where the picture doesn't reach is no shape: transparent, or the background color
    # of the brightness.
    canvas = QtGui.QImage(size, size, QtGui.QImage.Format.Format_ARGB32)
    if by_alpha:
        canvas.fill(QtCore.Qt.GlobalColor.transparent)
    else:
        canvas.fill(
            QtCore.Qt.GlobalColor.black if invert else QtCore.Qt.GlobalColor.white
        )
    painter = QtGui.QPainter(canvas)
    painter.drawImage(x, y, source)
    painter.end()

    mono = QtGui.QImage(size, size, QtGui.QImage.Format.Format_ARGB32)
    mono.fill(QtGui.QColor(color))
    if by_alpha:
        painter = QtGui.QPainter(mono)
        painter.setCompositionMode(
            QtGui.QPainter.CompositionMode.CompositionMode_DestinationIn
        )
        painter.drawImage(0, 0, canvas)
        painter.end()
        return mono

    brightness = canvas.convertToFormat(QtGui.QImage.Format.Format_Grayscale8)
    if not invert:
        brightness.invertPixels()  # dark is the shape
    mono.setAlphaChannel(brightness)
    return mono


def create_mono_icon(
    path: pathlib.Path | str,
    size: int = ICON_SIZE,
    color: QtGui.QColor | QtCore.Qt.GlobalColor = ICON_COLOR,
    invert: bool = False,
) -> QtGui.QIcon:
    """Make a one color icon of the shape in an image file, see `create_mono_image`.

    The icon has the given size and twice it, for screens with a higher pixel density.

    Args:
        path (pathlib.Path | str): image file or resource path (`:/icons/...`).
        size (int): pixel size of the icon.
        color (QtGui.QColor | Qt.GlobalColor): color of the shape, white like the icons
            of the editor by default.
        invert (bool): light parts are the shape. Only for an image with no
            transparency.

    Raises:
        FileNotFoundError: the file doesn't exist.
        ValueError: the file is not an image that can be read.

    Returns:
        QtGui.QIcon: icon.
    """
    icon = QtGui.QIcon()
    for pixel_size in (size, size * 2):
        image = create_mono_image(path, pixel_size, color, invert)
        icon.addPixmap(QtGui.QPixmap.fromImage(image))
    return icon
