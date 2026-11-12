import dataclasses

from PySide6 import QtGui


@dataclasses.dataclass
class StageRenderOptions:
    """How the editor draws the background of a stage.

    Attributes:
        grid_size: distance between two grid lines or dots
        grid_squares: number of grid cells between two major grid lines
        scene_width: width of the scene
        scene_height: height of the scene
        background_color: color the background is filled with
        grid_light_color: color of the minor grid lines
        grid_dark_color: color of the major grid lines
        grid_light_width: width of the minor grid lines
        grid_dark_width: width of the major grid lines
        dot_color: color of the dots
        dot_size: size of the dots on screen in whole pixels, it doesn't change
            with the zoom
        dots_min_spacing: dots are not drawn when they are closer than this on screen
    """

    grid_size: int = 20
    grid_squares: int = 5
    scene_width: int = 64000
    scene_height: int = 64000
    background_color: QtGui.QColor = dataclasses.field(
        default_factory=lambda: QtGui.QColor("#393939")
    )
    grid_light_color: QtGui.QColor = dataclasses.field(
        default_factory=lambda: QtGui.QColor("#2f2f2f")
    )
    grid_dark_color: QtGui.QColor = dataclasses.field(
        default_factory=lambda: QtGui.QColor("#292929")
    )
    grid_light_width: int = 1
    grid_dark_width: int = 2
    dot_color: QtGui.QColor = dataclasses.field(
        default_factory=lambda: QtGui.QColor("#4a4a4a")
    )
    dot_size: float = 2.0
    dots_min_spacing: float = 10.0
