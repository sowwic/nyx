"""Build the application icon files from the sized PNGs of the Nyx icon.

The `.icns` (macOS) and `.ico` (Windows) containers are written here, so no platform
tool (`iconutil`, `sips`, ImageMagick) is needed. Both formats can hold PNG images.

macOS draws app icons with a transparent margin around the artwork (see
`nyx.utils.app_icon.MACOS_ART_RATIO`), so a full-bleed icon looks too big in the
Dock. The source PNGs stay full-bleed, they are also used inside the application, and
Windows icons are meant to be full-bleed.
"""

import pathlib
import struct

from PySide6 import QtCore, QtGui

from nyx.utils.app_icon import pad_for_macos

# (icns type, pixel size). Types after `ic10` are the 2x variants of smaller sizes.
ICNS_TYPES = (
    ("icp4", 16),
    ("icp5", 32),
    ("icp6", 64),
    ("ic07", 128),
    ("ic08", 256),
    ("ic09", 512),
    ("ic10", 1024),
    ("ic11", 32),
    ("ic12", 64),
    ("ic13", 256),
    ("ic14", 512),
)
ICO_SIZES = (16, 32, 48, 64, 128, 256)


def find_source(source_dir: pathlib.Path, size: int) -> pathlib.Path:
    """Get the smallest source PNG that is at least `size` pixels wide.

    Args:
        source_dir (pathlib.Path): directory with `<size>.png` files.
        size (int): wanted pixel size.

    Returns:
        pathlib.Path: source image path.

    Raises:
        FileNotFoundError: no source image is large enough.
    """
    available = sorted(int(path.stem) for path in source_dir.glob("[0-9]*.png"))
    for candidate in available:
        if candidate >= size:
            return source_dir / f"{candidate}.png"
    raise FileNotFoundError(f"No icon of {size}px or larger in {source_dir}")


def render_png(source_dir: pathlib.Path, size: int, margin: bool = False) -> bytes:
    """Draw the icon at the given size.

    Args:
        source_dir (pathlib.Path): directory with `<size>.png` files.
        size (int): pixel size of the square image.
        margin (bool): leave the transparent margin macOS expects around the art.

    Returns:
        bytes: PNG image data.
    """
    image = QtGui.QImage(str(find_source(source_dir, size)))
    if margin:
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


def write_icns(source_dir: pathlib.Path, destination: pathlib.Path) -> None:
    """Write a macOS icon file, with the margin macOS expects.

    Args:
        source_dir (pathlib.Path): directory with `<size>.png` files.
        destination (pathlib.Path): `.icns` file path.
    """
    images = {size: render_png(source_dir, size, margin=True) for _, size in ICNS_TYPES}
    chunks = [
        icns_type.encode("ascii")
        + struct.pack(">I", 8 + len(images[size]))
        + images[size]
        for icns_type, size in ICNS_TYPES
    ]
    body = b"".join(chunks)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"icns" + struct.pack(">I", 8 + len(body)) + body)


def write_ico(source_dir: pathlib.Path, destination: pathlib.Path) -> None:
    """Write a Windows icon file.

    Args:
        source_dir (pathlib.Path): directory with `<size>.png` files.
        destination (pathlib.Path): `.ico` file path.
    """
    images = [render_png(source_dir, size) for size in ICO_SIZES]
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
