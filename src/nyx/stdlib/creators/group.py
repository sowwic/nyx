from PySide6 import QtCore

from nyx.api.v1 import CoreCreators, CoreUtilObjects
from nyx.api.v1.editor_utils import CreatorContext, UtilObjectCreator


class GroupCreator(UtilObjectCreator):
    """Creates a group around the selected nodes, or where the user clicked."""

    MARGIN = 24.0
    """float: space between a new group and the nodes it is created around."""
    TITLE_SPACE = 26.0
    """float: room above the nodes for the title of a new group."""

    @classmethod
    def get_type_id(cls) -> str:
        """str: id of the creator."""
        return CoreCreators.GROUP

    @classmethod
    def get_util_object_type_id(cls) -> str:
        """str: type id of the util object created."""
        return CoreUtilObjects.GROUP

    @classmethod
    def get_creation_geometry(
        cls, context: CreatorContext
    ) -> tuple[QtCore.QPointF, QtCore.QSizeF | None]:
        """Wrap the selected nodes, with room for the title above them.

        Args:
            context (CreatorContext): where the user wants to create.

        Returns:
            tuple[QtCore.QPointF, QtCore.QSizeF | None]: top left corner and size of
                the area around the nodes, the click position and the default size
                if no node is selected.
        """
        if context.selection_rect is None:
            return super().get_creation_geometry(context)
        bounds = context.selection_rect.adjusted(
            -cls.MARGIN, -cls.MARGIN - cls.TITLE_SPACE, cls.MARGIN, cls.MARGIN
        )
        return bounds.topLeft(), bounds.size()
