import enum

from PySide6 import QtGui, QtWidgets

MIN_TEXT_SIZE = 5.0
"""Smallest size of text, in points on screen, that is still drawn."""
MIN_SHAPE_SIZE = 4.0
"""Smallest size of a shape, in pixels on screen, that is still drawn."""


class LevelOfDetail(enum.IntEnum):
    """How much of a graph element is worth drawing at its size on screen.

    Levels are ordered, a higher level draws everything the lower ones do.
    """

    MINIMAL = 0
    """Shapes are too small to see, only a flat placeholder is drawn."""
    NO_TEXT = 1
    """Shapes are drawn, text is too small to read."""
    FULL = 2
    """Everything is drawn."""

    @property
    def shows_shapes(self) -> bool:
        """bool: shapes (sockets, pulses, icons) are drawn."""
        return self >= LevelOfDetail.NO_TEXT

    @property
    def shows_text(self) -> bool:
        """bool: text is drawn."""
        return self is LevelOfDetail.FULL

    @classmethod
    def from_scale(
        cls,
        scale: float,
        text_size: float | None = None,
        shape_size: float | None = None,
    ) -> LevelOfDetail:
        """Get the level of an element drawn at a scale.

        Args:
            scale (float): scale of the element on screen.
            text_size (float | None): size of its text in points. None if it has no
                text, which never limits the level.
            shape_size (float | None): size of its smallest shape in scene units.
                None if it has no shapes, which never limits the level.

        Returns:
            LevelOfDetail: level of detail to draw.
        """
        if shape_size is not None and shape_size * scale < MIN_SHAPE_SIZE:
            return cls.MINIMAL
        if text_size is not None and text_size * scale < MIN_TEXT_SIZE:
            return cls.NO_TEXT
        return cls.FULL

    @staticmethod
    def scale_from_painter(painter: QtGui.QPainter) -> float:
        """Get the scale an element is drawn with from the transform of the painter.

        The transform includes the view and all parents of the item, so this is the
        scale the element really has on screen, whatever view shows it.

        Args:
            painter (QtGui.QPainter): painter of the element.

        Returns:
            float: scale on screen.
        """
        return QtWidgets.QStyleOptionGraphicsItem.levelOfDetailFromTransform(
            painter.worldTransform()
        )

    @classmethod
    def from_painter(
        cls,
        painter: QtGui.QPainter,
        text_size: float | None = None,
        shape_size: float | None = None,
    ) -> LevelOfDetail:
        """Get the level of an element from the transform of the painter.

        The transform includes the view and all parents of the item, so this is the
        scale the element really has on screen, whatever view shows it.

        Args:
            painter (QtGui.QPainter): painter of the element.
            text_size (float | None): size of its text in points, if it has text.
            shape_size (float | None): size of its smallest shape in scene units, if it
                has shapes.

        Returns:
            LevelOfDetail: level of detail to draw.
        """
        return cls.from_scale(cls.scale_from_painter(painter), text_size, shape_size)
