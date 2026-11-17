"""Build the application icon files from the 1024px PNG of the Nyx icon.

The `.icns` (macOS) is made with `iconutil`, which writes the layout Finder expects,
the hand-packed one showed a bad icon in Finder list views. The `.ico` (Windows) is
written here, the format can hold PNG images.

macOS draws app icons with a transparent margin around the artwork (see
`nyx.utils.app_icon.MACOS_ART_RATIO`), so a full-bleed icon looks too big in the
Dock. The source PNGs stay full-bleed, they are also used inside the application, and
Windows icons are meant to be full-bleed. Sizes below `MIN_PADDED_SIZE` stay
full-bleed on macOS too: Finder shows them in list views, and the margin would leave
only a few pixels for the artwork.
"""

import pathlib
import struct
import subprocess
import tempfile

from PySide6 import QtCore, QtGui

from nyx.utils.app_icon import MIN_PADDED_SIZE, pad_for_macos

# Names of the images of an iconset, with their pixel size.
ICONSET_IMAGES = {
    "icon_16x16": 16,
    "icon_16x16@2x": 32,
    "icon_32x32": 32,
    "icon_32x32@2x": 64,
    "icon_128x128": 128,
    "icon_128x128@2x": 256,
    "icon_256x256": 256,
    "icon_256x256@2x": 512,
    "icon_512x512": 512,
    "icon_512x512@2x": 1024,
}
ICO_SIZES = (16, 32, 48, 64, 128, 256)


def render_png(source: pathlib.Path, size: int, margin: bool = False) -> bytes:
    """Draw the icon at the given size.

    Args:
        source (pathlib.Path): full-bleed source PNG, at least as big as `size`.
        size (int): pixel size of the square image.
        margin (bool): leave the transparent margin macOS expects around the art, for
            sizes of `MIN_PADDED_SIZE` and above.

    Returns:
        bytes: PNG image data.
    """
    image = QtGui.QImage(str(source))
    if margin and size >= MIN_PADDED_SIZE:
        canvas = pad_for_macos(image, size)
    else:
        canvas = image.scaled(
            size,
            size,
            QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        ).convertToFormat(QtGui.QImage.Format.Format_ARGB32)

    data = QtCore.QByteArray()
    buffer = QtCore.QBuffer(data)
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    canvas.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def write_icns(source: pathlib.Path, destination: pathlib.Path) -> None:
    """Write a macOS icon file with `iconutil`, with the margin macOS expects.

    Args:
        source (pathlib.Path): full-bleed source PNG, at least as big as `size`.
        destination (pathlib.Path): `.icns` file path.

    Raises:
        subprocess.CalledProcessError: `iconutil` failed.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        iconset = pathlib.Path(temp_dir) / "nyx.iconset"
        iconset.mkdir()
        for name, size in ICONSET_IMAGES.items():
            (iconset / f"{name}.png").write_bytes(render_png(source, size, margin=True))
        subprocess.run(
            [
                "iconutil",
                "--convert",
                "icns",
                "--output",
                str(destination),
                str(iconset),
            ],
            check=True,
        )


def write_ico(source: pathlib.Path, destination: pathlib.Path) -> None:
    """Write a Windows icon file.

    Args:
        source (pathlib.Path): full-bleed source PNG, at least as big as `size`.
        destination (pathlib.Path): `.ico` file path.
    """
    images = [render_png(source, size) for size in ICO_SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries = []
    for size, image in zip(ICO_SIZES, images):
        # A width or height of 256 is stored as 0.
        dimension = size if size < 256 else 0
        entries.append(
            struct.pack(
                "<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(image), offset
            )
        )
        offset += len(image)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(header + b"".join(entries) + b"".join(images))
