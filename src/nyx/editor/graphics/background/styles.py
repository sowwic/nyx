from nyx.core.stage_render_options import StageRenderOptions
from nyx.editor.graphics.background.dots_background import DotsBackground
from nyx.editor.graphics.background.grid_background import GridBackground
from nyx.editor.graphics.background.stage_background import StageBackground
from nyx.static.enums import StageBackGroundStyle

BACKGROUND_CLASSES: dict[StageBackGroundStyle, type[StageBackground]] = {
    StageBackGroundStyle.GRID: GridBackground,
    StageBackGroundStyle.DOTS: DotsBackground,
}
"""Background class of every style."""


def create_background(
    style: StageBackGroundStyle, options: StageRenderOptions
) -> StageBackground:
    """Create the background of a style.

    Args:
        style (StageBackGroundStyle): style of the background.
        options (StageRenderOptions): options the background draws with.

    Returns:
        StageBackground: new background.
    """
    return BACKGROUND_CLASSES[style](options)
