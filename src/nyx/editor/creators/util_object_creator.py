from __future__ import annotations

import typing

from PySide6 import QtCore

from nyx.core import commands
from nyx.core.plugin_subsystem.registry import NYX_REGISTRY
from .creator import Creator, CreatorContext

if typing.TYPE_CHECKING:
    from nyx.core.util_object import UtilObject


class UtilObjectCreator(Creator):
    """Creator of util objects of one type, at the place the user clicked.

    Subclasses implement `get_type_id` and `get_util_object_type_id`. The name, icon and
    description of the menu entry come from the util object type. Override
    `get_creation_geometry` to choose the position and size (a group wraps the selected
    nodes) and `get_creation_properties` to start with more than the defaults.
    """

    @classmethod
    def get_util_object_type_id(cls) -> str:
        """str: type id of the util object created. Subclasses must implement."""
        raise NotImplementedError

    @classmethod
    def get_util_object_cls(cls) -> type[UtilObject] | None:
        """type[UtilObject] | None: class of the util object, None if not registered."""
        return NYX_REGISTRY.util_objects.get(cls.get_util_object_type_id())

    @classmethod
    def get_display_name(cls) -> str:
        """str: display name of the util object type."""
        util_object_cls = cls.get_util_object_cls()
        if util_object_cls is None:
            return cls.get_util_object_type_id()
        return util_object_cls.get_type_display_name()

    @classmethod
    def get_icon(cls) -> str:
        """str: icon of the util object type."""
        util_object_cls = cls.get_util_object_cls()
        if util_object_cls is None:
            return super().get_icon()
        return util_object_cls.get_type_icon()

    @classmethod
    def get_description(cls) -> str:
        """str: description of the util object type."""
        util_object_cls = cls.get_util_object_cls()
        return "" if util_object_cls is None else util_object_cls.get_description()

    @classmethod
    def get_creation_geometry(
        cls, context: CreatorContext
    ) -> tuple[QtCore.QPointF, QtCore.QSizeF | None]:
        """Choose where the object goes and how big it is.

        Args:
            context (CreatorContext): where the user wants to create.

        Returns:
            tuple[QtCore.QPointF, QtCore.QSizeF | None]: top left corner in scene
                coordinates, and the size, None for the default size of the type.
        """
        return context.position, None

    @classmethod
    def get_creation_properties(
        cls, context: CreatorContext
    ) -> dict[str, typing.Any] | None:
        """Choose properties the object starts with besides position and size.

        Args:
            context (CreatorContext): where the user wants to create.

        Returns:
            dict[str, typing.Any] | None: values as listed by
                `UtilObject.serialize_properties`, None for the defaults.
        """
        return None

    @classmethod
    def create(cls, context: CreatorContext) -> UtilObject | None:
        """Create the util object.

        Args:
            context (CreatorContext): where the user wants to create.

        Returns:
            UtilObject | None: created object.
        """
        position, size = cls.get_creation_geometry(context)
        command = commands.CreateUtilObjectCommand(
            context.stage,
            cls.get_util_object_type_id(),
            node=context.scope_node,
            position=position,
            size=size,
            properties=cls.get_creation_properties(context),
        )
        context.stage.push_command(command)
        return command.result_object
