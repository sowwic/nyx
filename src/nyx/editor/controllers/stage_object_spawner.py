from __future__ import annotations

import dataclasses
import logging
import typing

from PySide6 import QtCore, QtWidgets

from nyx.core.exceptions import NyxCommandValidationError

if typing.TYPE_CHECKING:
    from nyx.application import NyxEditorApplication
    from nyx.core.commands._base_nyx_command import NyxCommand
    from nyx.core.node import Node
    from nyx.core.stage import Stage
    from nyx.core.stage_object import StageObject
    from nyx.editor.widgets.stage_graph_editor import StageGraphEditor

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class SpawnContext:
    """Where and with what a spawner is asked to create something.

    Attributes:
        graph_editor: editor of the graph the user is in.
        stage: stage of the editor.
        scope_node: node whose contents are drawn, the new object goes in it.
        position: place the user asked for, in scene coordinates.
        selection_rect: area taken by the selected nodes in scene coordinates, None
            when no node is selected.
    """

    graph_editor: StageGraphEditor
    stage: Stage
    scope_node: Node
    position: QtCore.QPointF
    selection_rect: QtCore.QRectF | None = None

    @property
    def is_scope_locked(self) -> bool:
        """bool: nothing can be added to the scope, it belongs to a reference."""
        return self.scope_node.locks_children


class StageObjectSpawner(QtCore.QObject):
    """Base of the classes that create stage objects when the user asks for them.

    A spawner pushes a create command to the stage, so the creation is one undo step,
    and tells who is interested with `spawned`. A command the stage refuses, such as one
    in a scope that is locked, gives a warning and nothing is created.

    `NodeSpawner` and `NodeComponentSpawner` create what the user picked in a list. A
    spawner can also be an entry of the Create menu of the graph view: register it in
    `NyxPluginContents.spawners` and implement the menu contract below, or subclass
    `UtilObjectSpawner`, which does for util objects.

    Attributes:
        spawned: emitted with the stage object that was created.
    """

    spawned = QtCore.Signal(object)

    @property
    def current_stage_graph(self) -> StageGraphEditor | None:
        """StageGraphEditor | None: editor of the active window."""
        application: NyxEditorApplication = QtWidgets.QApplication.instance()
        return application.main_window().current_stage_graph

    @property
    def stage(self) -> Stage | None:
        """Stage | None: stage of the active editor."""
        current_editor = self.current_stage_graph
        if current_editor is None:
            return None
        return current_editor.stage

    def _spawn(
        self,
        stage: Stage,
        command: NyxCommand,
        get_result: typing.Callable[[], StageObject],
    ) -> StageObject | None:
        """Push a create command and report what it created.

        Args:
            stage (Stage): stage the command is for.
            command (NyxCommand): command that creates the object.
            get_result (typing.Callable[[], StageObject]): reads the created object
                from the command, once it ran.

        Returns:
            StageObject | None: created object, None if the stage refused the command.
        """
        try:
            stage.push_command(command)
        except NyxCommandValidationError as err:
            LOGGER.warning(str(err))
            return None
        result = get_result()
        self.spawned.emit(result)
        return result

    # ---- Create menu contract: what a registered spawner implements ----
    @classmethod
    def get_type_id(cls) -> str:
        """str: unique id of the spawner, the key in the registry. Implement it."""
        raise NotImplementedError

    @classmethod
    def get_display_name(cls) -> str:
        """str: text of the menu entry. Implement it."""
        raise NotImplementedError

    @classmethod
    def get_icon(cls) -> str:
        """str: resource path of the icon of the menu entry."""
        return ":/icons/plus"

    @classmethod
    def get_description(cls) -> str:
        """str: tooltip of the menu entry, empty for none."""
        return ""

    @classmethod
    def is_available(cls, context: SpawnContext) -> bool:
        """Check whether the spawner can be used where the user is.

        Args:
            context (SpawnContext): where the user wants to create.

        Returns:
            bool: the menu entry is enabled. Defaults to the scope accepting new
                objects.
        """
        return not context.is_scope_locked

    def spawn(self, context: SpawnContext) -> StageObject | None:
        """Create something. Implement it.

        Args:
            context (SpawnContext): where the user wants to create.

        Returns:
            StageObject | None: created node or util object, which the editor
                selects. None if there is nothing to select.
        """
        raise NotImplementedError
