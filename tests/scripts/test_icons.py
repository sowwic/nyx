import pathlib
import shutil
import struct
import subprocess

import pytest
from PySide6 import QtGui

import icons

SOURCE = pathlib.Path(__file__).resolve().parents[2] / "src/nyx/resources/icons/nyx.png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def decode(data: bytes) -> QtGui.QImage:
    image = QtGui.QImage()
    assert image.loadFromData(data, "PNG")
    return image


def test_render_png_without_margin_fills_the_canvas():
    image = decode(icons.render_png(SOURCE, 256))

    assert (image.width(), image.height()) == (256, 256)
    assert image.pixelColor(128, 128).alpha() == 255
    assert image.pixelColor(10, 128).alpha() == 255


def test_render_png_with_margin_leaves_the_edges_transparent():
    image = decode(icons.render_png(SOURCE, 256, margin=True))

    assert (image.width(), image.height()) == (256, 256)
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(10, 128).alpha() == 0
    assert image.pixelColor(128, 128).alpha() == 255


def test_small_sizes_stay_full_bleed_with_the_margin_option():
    image = decode(icons.render_png(SOURCE, 32, margin=True))

    assert (image.width(), image.height()) == (32, 32)
    assert image.pixelColor(1, 16).alpha() == 255


@pytest.mark.skipif(shutil.which("iconutil") is None, reason="needs macOS iconutil")
def test_write_icns_round_trips_through_iconutil(tmp_path):
    destination = tmp_path / "out" / "nyx.icns"
    iconset = tmp_path / "nyx.iconset"

    icons.write_icns(SOURCE, destination)
    subprocess.run(
        ["iconutil", "--convert", "iconset", "--output", str(iconset), str(destination)],
        check=True,
    )

    assert destination.read_bytes()[:4] == b"icns"
    for name, size in icons.ICONSET_IMAGES.items():
        assert decode((iconset / f"{name}.png").read_bytes()).width() == size


def test_write_ico_has_a_valid_container(tmp_path):
    destination = tmp_path / "nyx.ico"

    icons.write_ico(SOURCE, destination)

    data = destination.read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind, count) == (0, 1, len(icons.ICO_SIZES))
    for index, size in enumerate(icons.ICO_SIZES):
        entry = data[6 + 16 * index : 6 + 16 * (index + 1)]
        width, height, _, _, planes, bits, length, offset = struct.unpack(
            "<BBBBHHII", entry
        )
        assert (width, height) == ((size, size) if size < 256 else (0, 0))
        assert (planes, bits) == (1, 32)
        payload = data[offset : offset + length]
        assert payload.startswith(PNG_SIGNATURE)
        assert decode(payload).width() == size
