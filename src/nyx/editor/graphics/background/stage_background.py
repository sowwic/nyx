from PySide6 import QtCore, QtGui

from nyx.core.stage_render_options import StageRenderOptions


class StageBackground:
    """Draws the pattern of a graphics stage background.

    Subclasses implement `draw`. Add one to `BACKGROUND_CLASSES` to make it a style.
    """

    def __init__(self, options: StageRenderOptions):
        """Initializes the background with the options it draws with.

        Args:
            options (StageRenderOptions): colors and sizes of the pattern.
        """
        self.options = options

    def draw(self, painter: QtGui.QPainter, rect: QtCore.QRectF):
        """Draws the pattern over the exposed rect.

        Args:
            painter (QPainter): painter of the scene, with the scene transform.
            rect (QRectF): exposed part of the scene.
        """
        raise NotImplementedError
