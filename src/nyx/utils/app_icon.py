"""Application icon, shared by the running app and the icon file build script."""

from PySide6 import QtCore, QtGui

# macOS draws app icons with a transparent margin around the artwork, so a full-bleed
# icon looks too big in the Dock.
MACOS_ART_RATIO = 840 / 1024


def pad_for_macos(image: QtGui.QImage, size: int | None = None) -> QtGui.QImage:
    """Shrink the artwork to the macOS ratio, centered on a transparent canvas.

    Args:
        image (QtGui.QImage): square full-bleed icon image.
        size (int | None): pixel size of the result, the image size by default.

    Returns:
        QtGui.QImage: square image with a transparent margin.
    """
    size = size or image.width()
    art_size = round(size * MACOS_ART_RATIO)
    art = image.scaled(
        art_size,
        art_size,
        QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )
    canvas = QtGui.QImage(size, size, QtGui.QImage.Format.Format_ARGB32)
    canvas.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(canvas)
    painter.drawImage((size - art_size) // 2, (size - art_size) // 2, art)
    painter.end()
    return canvas
