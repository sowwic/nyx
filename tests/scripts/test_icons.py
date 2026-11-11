import pathlib
import struct

import pytest
from PySide6 import QtGui

import icons

SOURCE_DIR = pathlib.Path(__file__).resolve().parents[2] / (
    "src/nyx/resources/icons/nyx"
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def decode(data: bytes) -> QtGui.QImage:
    image = QtGui.QImage()
    assert image.loadFromData(data, "PNG")
    return image


def test_find_source_uses_the_smallest_image_that_is_large_enough():
    assert icons.find_source(SOURCE_DIR, 16).name == "64.png"
    assert icons.find_source(SOURCE_DIR, 256).name == "256.png"
    assert icons.find_source(SOURCE_DIR, 300).name == "512.png"


def test_find_source_fails_when_nothing_is_large_enough():
    with pytest.raises(FileNotFoundError):
        icons.find_source(SOURCE_DIR, 4096)


def test_render_png_without_margin_fills_the_canvas():
    image = decode(icons.render_png(SOURCE_DIR, 256))

    assert (image.width(), image.height()) == (256, 256)
    assert image.pixelColor(128, 128).alpha() == 255
    assert image.pixelColor(10, 128).alpha() == 255


def test_render_png_with_margin_leaves_the_edges_transparent():
    image = decode(icons.render_png(SOURCE_DIR, 256, margin=True))

    assert (image.width(), image.height()) == (256, 256)
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(10, 128).alpha() == 0
    assert image.pixelColor(128, 128).alpha() == 255


def test_write_icns_has_a_valid_container(tmp_path):
    destination = tmp_path / "out" / "nyx.icns"

    icons.write_icns(SOURCE_DIR, destination)

    data = destination.read_bytes()
    assert data[:4] == b"icns"
    assert struct.unpack(">I", data[4:8])[0] == len(data)
    sizes_by_type = {}
    offset = 8
    while offset < len(data):
        chunk_type = data[offset : offset + 4].decode("ascii")
        length = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
        payload = data[offset + 8 : offset + length]
        assert payload.startswith(PNG_SIGNATURE)
        sizes_by_type[chunk_type] = decode(payload).width()
        offset += length
    assert offset == len(data)
    assert sizes_by_type == dict(icons.ICNS_TYPES)


def test_write_ico_has_a_valid_container(tmp_path):
    destination = tmp_path / "nyx.ico"

    icons.write_ico(SOURCE_DIR, destination)

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
