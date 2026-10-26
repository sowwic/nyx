import logging
import typing

from PySide6 import QtWidgets

from nyx.core.plugin_subsystem.registry import NYX_REGISTRY

if typing.TYPE_CHECKING:
    from nyx.core.stage_object import StageObject


LOGGER = logging.getLogger(__name__)


def register_builtin_graphics_objects() -> None:
    """Register the graphics objects drawing nodes, plugs and links.

    The ones drawing the util objects of the standard library come with its plugin.
    """
    from nyx.editor.graphics.graphics_link import GraphicsLink
    from nyx.editor.graphics.graphics_node import GraphicsNode
    from nyx.editor.graphics.graphics_plug import GraphicsPlug

    for graphics_cls in (GraphicsNode, GraphicsPlug, GraphicsLink):
        NYX_REGISTRY.register_builtin_graphics_object(
            graphics_cls.get_type_id(), graphics_cls
        )


def create_graphics_object(
    stage_object: StageObject, *args: typing.Any, **kwargs: typing.Any
) -> QtWidgets.QGraphicsItem:
    """Create the graphics object that draws a stage object.

    The class is looked up in the registry by the `graphics_object_id` of the stage
    object. An id that isn't registered falls back to the default of its type.

    Args:
        stage_object (StageObject): node, component, link or util object to draw.
        *args: positional arguments for the graphics object.
        **kwargs: keyword arguments for the graphics object.

    Returns:
        QtWidgets.QGraphicsItem: new graphics object.
    """
    graphics_id = stage_object.graphics_object_id
    graphics_cls = NYX_REGISTRY.get_graphics_object_cls(graphics_id)
    if graphics_cls is None:
        default_id = type(stage_object).GRAPHICS_OBJECT_ID
        LOGGER.warning(
            "Unknown graphics object %r of %s, using %r",
            graphics_id,
            stage_object,
            default_id,
        )
        graphics_cls = NYX_REGISTRY.get_graphics_object_cls(default_id)
    return graphics_cls(*args, **kwargs)
