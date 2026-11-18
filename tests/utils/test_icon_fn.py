import pytest
from PySide6 import QtCore, QtGui

from nyx.utils import icon_fn

SIZE = 24


@pytest.fixture
def make_image(tmp_path):
    """Save an image made by a function that paints on it, return its path."""

    def _make(name, width, height, paint, fmt=QtGui.QImage.Format.Format_ARGB32):
        image = QtGui.QImage(width, height, fmt)
        painter = QtGui.QPainter(image)
        paint(image, painter)
        painter.end()
        path = tmp_path / name
        assert image.save(str(path))
        return path

    return _make


def alpha_at(image, x, y):
    return image.pixelColor(x, y).alpha()


def paint_red_square_on_transparent(image, painter):
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter.fillRect(8, 8, 16, 16, QtGui.QColor(220, 30, 30))


def paint_black_square_on_white(image, painter):
    image.fill(QtCore.Qt.GlobalColor.white)
    painter.fillRect(8, 8, 16, 16, QtCore.Qt.GlobalColor.black)


def test_transparent_image_keeps_its_shape_in_white(qapp, make_image):
    path = make_image("red.png", 32, 32, paint_red_square_on_transparent)

    image = icon_fn.create_mono_image(path)

    assert (image.width(), image.height()) == (SIZE, SIZE)
    inside = image.pixelColor(SIZE // 2, SIZE // 2)
    assert (inside.red(), inside.green(), inside.blue(), inside.alpha()) == (
        255,
        255,
        255,
        255,
    )
    assert alpha_at(image, 1, 1) == 0


def test_every_visible_pixel_has_the_one_color(qapp, make_image):
    path = make_image("red.png", 32, 32, paint_red_square_on_transparent)

    image = icon_fn.create_mono_image(path, color=QtGui.QColor(10, 20, 30))

    colors = {
        image.pixelColor(x, y).getRgb()[:3]
        for y in range(SIZE)
        for x in range(SIZE)
        if alpha_at(image, x, y) > 0
    }
    assert colors == {(10, 20, 30)}


def test_image_without_transparency_is_shaped_by_its_dark_parts(qapp, make_image):
    path = make_image(
        "black_on_white.png",
        32,
        32,
        paint_black_square_on_white,
        QtGui.QImage.Format.Format_RGB32,
    )

    image = icon_fn.create_mono_image(path)

    assert alpha_at(image, SIZE // 2, SIZE // 2) == 255
    assert alpha_at(image, 1, 1) == 0
    assert image.pixelColor(SIZE // 2, SIZE // 2).getRgb()[:3] == (255, 255, 255)


def test_invert_makes_the_light_parts_the_shape(qapp, make_image):
    path = make_image(
        "black_on_white.png",
        32,
        32,
        paint_black_square_on_white,
        QtGui.QImage.Format.Format_RGB32,
    )

    image = icon_fn.create_mono_image(path, invert=True)

    assert alpha_at(image, SIZE // 2, SIZE // 2) == 0
    assert alpha_at(image, 1, 1) == 255


def test_image_that_is_not_square_is_centered_with_its_proportions(qapp, make_image):
    def paint(image, painter):
        image.fill(QtCore.Qt.GlobalColor.transparent)
        painter.fillRect(0, 0, 64, 32, QtGui.QColor(0, 0, 0))

    path = make_image("wide.png", 64, 32, paint)

    image = icon_fn.create_mono_image(path)

    assert alpha_at(image, SIZE // 2, SIZE // 2) == 255
    assert alpha_at(image, SIZE // 2, 1) == 0  # margin above
    assert alpha_at(image, SIZE // 2, SIZE - 2) == 0  # margin below
    assert alpha_at(image, 1, SIZE // 2) == 255  # full width


def test_icon_has_the_size_and_twice_it(qapp, make_image):
    path = make_image("red.png", 32, 32, paint_red_square_on_transparent)

    icon = icon_fn.create_mono_icon(path)

    assert not icon.isNull()
    assert {(size.width(), size.height()) for size in icon.availableSizes()} == {
        (SIZE, SIZE),
        (SIZE * 2, SIZE * 2),
    }


def test_custom_size_is_used(qapp, make_image):
    path = make_image("red.png", 32, 32, paint_red_square_on_transparent)

    assert icon_fn.create_mono_image(path, size=16).width() == 16


def test_resource_path_is_read(qapp):
    image = icon_fn.create_mono_image(":/icons/settings.png")

    assert alpha_at(image, SIZE // 2, SIZE // 2) > 0 or any(
        alpha_at(image, x, y) > 0 for x in range(SIZE) for y in range(SIZE)
    )


def test_missing_file_raises(qapp, tmp_path):
    with pytest.raises(FileNotFoundError):
        icon_fn.create_mono_icon(tmp_path / "missing.png")


def test_file_that_is_not_an_image_raises(qapp, tmp_path):
    path = tmp_path / "text.png"
    path.write_text("not an image")

    with pytest.raises(ValueError):
        icon_fn.create_mono_icon(path)
