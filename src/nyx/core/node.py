import enum
import typing
import time
import pathlib
from collections import deque
from collections import OrderedDict
from PySide2 import QtCore
from PySide2 import QtGui

from nyx.core.attribute import Attribute
from nyx.core.serializable import Serializable
from nyx.core import nyx_exceptions
from nyx.utils import inspect_fn
from nyx.utils import file_fn
from nyx import get_main_logger

if typing.TYPE_CHECKING:
    from nyx.core import Stage
    from nyx.editor.graphics.graphics_node import GraphicsNode


LOGGER = get_main_logger()


class NodeSignals(QtCore.QObject):
    renamed = QtCore.Signal(pathlib.PurePosixPath, pathlib.PurePosixPath)
    active_state_changed = QtCore.Signal(bool)
    execution_started = QtCore.Signal()
    execution_succeed = QtCore.Signal()
    execution_failed = QtCore.Signal()
    attr_added = QtCore.Signal(Attribute)
    attr_deleted = QtCore.Signal(str)
    attr_renamed = QtCore.Signal(str, str)
    input_exec_changed = QtCore.Signal()
    output_exec_changed = QtCore.Signal()


class Node(QtGui.QStandardItem, Serializable):

    class Roles(enum.Enum):
        ATTRIBUTES_ROLE: int = QtCore.Qt.UserRole + 1
        PYTHON_CODE_ROLE: int = enum.auto()
        INPUT_EXEC_ROLE: int = enum.auto()
        OUTPUT_EXEC_ROLE: int = enum.auto()
        ACTIVE_ROLE: int = enum.auto()
        EXECUTION_START_PATH_ROLE: int = enum.auto()
        POSITION_ROLE: int = enum.auto()
        COMMENT_ROLE: int = enum.auto()

    def __init__(self,
                 name: str = "node",
                 parent: "Node | pathlib.PurePosixPath | str | None" = None) -> None:
        QtGui.QStandardItem.__init__(self, name)
        Serializable.__init__(self)
        self.gr_node: "GraphicsNode" = None
        self.signals = NodeSignals()

        self.setData(OrderedDict(), role=Node.Roles.ATTRIBUTES_ROLE.value)
        self.setData(str(), role=Node.Roles.PYTHON_CODE_ROLE.value)
        self.setData(None, role=Node.Roles.INPUT_EXEC_ROLE.value)
        self.setData(None, role=Node.Roles.OUTPUT_EXEC_ROLE.value)
        self.setData(True, role=Node.Roles.ACTIVE_ROLE.value)
        self.setData(None, role=Node.Roles.EXECUTION_START_PATH_ROLE.value)
        self.setData(QtCore.QPointF(), role=Node.Roles.POSITION_ROLE.value)
        self.setData("", role=Node.Roles.COMMENT_ROLE.value)

        self._cached_path = None

        if parent:
            parent.appendRow(self)

    def __repr__(self) -> str:
        return f"{inspect_fn.class_string(self.__class__)} ({self.cached_path})"

    def __hash__(self) -> int:
        return hash(self.path)

    def __getitem__(self, key) -> Attribute:
        try:
            return self.attribs[key]
        except KeyError:
            raise nyx_exceptions.NodeNoAttributeExistError

    def __setitem__(self, key: str, value):
        data = self.attribs
        if key not in data:
            data[key] = Attribute(self, value)
            LOGGER.debug(f"{self} | Added {data[key]}")
        else:
            data[key].set(value)
        self.setData(data, role=Node.Roles.ATTRIBUTES_ROLE.value)

    @property
    def name(self):
        """Node name

        Returns:
            str: name.
        """
        return self.text()

    @property
    def scope(self):
        return tuple(self.path.parents)[0]

    @property
    def path(self) -> pathlib.PurePosixPath:
        """Get current node path.

        Returns:
            pathlib.PurePosixPath: absolute node path.
        """
        path = pathlib.PurePosixPath("/")
        if not self.parent():
            return path / self.name
        return self.parent().path / self.name

    @property
    def cached_path(self):
        return self._cached_path

    @property
    def stage(self) -> "Stage":
        """Utility method pointing to node's stage (model).

        Returns:
            Stage: stage node belongs to.
        """
        return self.model()

    @property
    def attribs(self) -> "OrderedDict[str, Attribute]":
        """Node attributes dictionnary.

        Returns:
            OrderedDict[str, Attribute]: Node attributes.
        """
        return self.data(role=Node.Roles.ATTRIBUTES_ROLE.value)

    @property
    def python_code(self) -> str:
        """Node python code.

        Returns:
            str: python code string.
        """
        return self.data(role=self.Roles.PYTHON_CODE_ROLE.value)

    def cache_current_path(self):
        """Store current path in cache."""
        self._cached_path = self.path

    def is_active(self) -> bool:
        """Query if node's active state.

        Returns:
            bool: current active state.
        """
        return self.data(role=Node.Roles.ACTIVE_ROLE.value)

    def set_active(self, state: bool):
        """Set active state.

        Args:
            state (bool): new active state.
        """
        self.setData(state, role=Node.Roles.ACTIVE_ROLE.value)
        self.signals.active_state_changed.emit(state)

    def deactivate(self):
        """Set node's active state to False."""
        self.set_active(False)

    def activate(self):
        """Set node's active state to True."""
        self.set_active(True)

    def position(self) -> QtCore.QPointF:
        return self.data(role=Node.Roles.POSITION_ROLE.value)

    def serializable_position(self):
        position = self.position()
        return [position.x(), position.y()]

    def set_position(self, position: QtCore.QPointF):
        self.setData(position, role=Node.Roles.POSITION_ROLE.value)

    def comment(self) -> str:
        return self.data(role=Node.Roles.COMMENT_ROLE.value)

    def set_comment(self, text: str):
        self.setData(text, role=Node.Roles.COMMENT_ROLE.value)

    def appendRow(self, items: typing.Sequence["Node"]) -> None:
        """Override Qt method.

        - Generates new unique name.
        - Set cached path to current.
        - Store path into stage path map.

        Args:
            items (typing.Sequence): items to append.

        Raises:
            ValueError: path exists in stage path map.
        """
        if not isinstance(items, typing.Sequence):
            items = [items]

        for node in items:
            unique_name = self.stage.generate_unique_node_name(
                node.name, parent_node=self)
            new_path = self.path / unique_name
            if new_path in self.stage.path_map:
                LOGGER.error(f"Duplicate path: {new_path}")
                raise ValueError

            node.setText(unique_name)
            super().appendRow(node)
            assert node.path == new_path
            LOGGER.debug(f"{self} | added child node {new_path}")

            node.cache_current_path()
            self.stage._path_map[node.path] = node

    def rename(self, new_name: str):
        """Rename node.

        - Also update path for self and children in path map.

        Args:
            new_name (str): new node name.
        """
        if new_name == self.name:
            return

        old_path = self.cached_path
        new_name = self.stage.generate_unique_node_name(
            new_name, parent_node=self.parent())
        self.setText(new_name)
        self._update_pathmap_entry()
        self.signals.renamed.emit(old_path, self.cached_path)

    def _update_pathmap_entry(self):
        """Update path stored for in stage path map."""
        self.stage._path_map.pop(self.cached_path)
        self.stage._path_map[self.path] = self
        self.cache_current_path()
        for child_node in self.list_children():
            child_node._update_pathmap_entry()

    def child_names_set(self):
        """Get set of existing child names.

        Returns:
            set[str]: child names.
        """
        return {node.text() for node in self.list_children()}

    def list_children(self) -> "list[Node]":
        """List child nodes.

        Returns:
            list[Node]: child nodes.
        """
        children = [self.child(row) for row in range(self.rowCount())]
        return children

    def list_children_paths(self) -> "list[pathlib.PurePosixPath]":
        """List of child paths.

        Returns:
            list[pathlib.PurePosixPath]: child paths.
        """
        return [child_node.cached_path for child_node in self.list_children()]

    def list_children_tree(self) -> "list[Node]":
        """List children tree recursively.

        Returns:
            list[Node]: child nodes tree.
        """
        children = self.list_children()
        for child in children:
            children += child.list_children()
        return children

    def is_parent_of(self, other_node: "Node | str | pathlib.PurePosixPath"):
        """Check if given path is path of one of the child nodes.

        Args:
            path (str | pathlib.PurePosixPath): path to test.

        Returns:
            bool: if path belongs to one of children.
        """
        other_node = self.stage.node(other_node)
        return other_node in set(self.list_children())

    def list_parents(self, as_queue=False) -> "list[Node] | deque[Node]":
        """List parents recursively.

        Args:
            as_queue (bool, optional): if result should be returned as deque. Defaults to False.

        Returns:
            list[Node] | deque[Node]: parent nodes collection.
        """
        parents = deque()
        if self.parent():
            parents.appendleft(self.parent())
            parents.extendleft(self.parent().list_parents())
        return parents if as_queue else list(parents)

    def delete(self):
        """Delete this node from stage."""
        self.stage.delete_node(self)

    def add_attr(self, name: str, value=None, resolve=True):
        name = self.generate_unique_attr_name(name)
        self[name] = value
        if resolve:
            self[name].resolve()
        self.signals.attr_added.emit(self[name])
        return self[name]

    def generate_unique_attr_name(self, name: str):
        if name in self.attribs.keys():
            index = 1
            while name + str(index) in self.attribs.keys():
                index += 1
            return name + str(index)
        return name

    def attr(self, name: str) -> Attribute:
        """Get attribute with name.

        Args:
            name (str): attribute name.

        Returns:
            Attribute: attribute instance.
        """
        return self[name]

    def set_attr(self, name: str, value: typing.Any):
        """Set raw attribute value.

        Args:
            name (str): attribute name.
            value (typing.Any): new value.
        """
        self[name] = value

    def delete_attr(self, name: str):
        """Delete attribute.

        Args:
            name (str): attribute name.
        """
        data = self.attribs
        if name not in data.keys():
            LOGGER.warning(
                f"Can't delete attribute {name} that doesn't exist!")
            return
        data.pop(name)
        self.setData(data, role=Node.Roles.ATTRIBUTES_ROLE.value)
        self.signals.attr_deleted.emit(name)
        LOGGER.debug(f"{self} | deleted attr {name}")

    def rename_attr(self, name: str, new_name: str):
        """Rename attribute.

        Args:
            name (str): attribute name.
            new_name (str): new attribute name.
        """
        if not new_name:
            LOGGER.error("New attribute name can't be empty string!")
            return

        data = self.attribs
        if name not in data.keys():
            LOGGER.warning(
                f"Can't rename attribute {name} that doesn't exist!")
            return

        new_name = self.generate_unique_attr_name(new_name)
        data[new_name] = data.pop(name)
        self.setData(data, role=Node.Roles.ATTRIBUTES_ROLE.value)
        self.signals.attr_renamed.emit(name, new_name)
        return data[new_name]

    def stacked_attribs(self):
        """Dictionary of merged dictionaries.

        parent: {a: 5, b: 10}, child: {a: 15} -> result: {a: 15, b: 10}

        Returns:
            OrderedDict: merged dictionary.
        """
        stacked_attrs = OrderedDict()
        for parent in self.list_parents(as_queue=True):
            stacked_attrs.update(parent.attribs)
        stacked_attrs.update(self.attribs)
        return stacked_attrs

    def get_input_exec_path(self, serializable=False) -> "pathlib.PurePosixPath | str | None":
        """Get path for the node that is set as execution dependency.

        Args:
            serializable (bool, optional): Return value is serializable. Defaults to False.

        Returns:
            pathlib.PurePosixPath | str | None: Execution dependency node path.
        """
        path: pathlib.PurePosixPath = self.data(
            role=Node.Roles.INPUT_EXEC_ROLE.value)
        if path is None or not serializable:
            return path
        return path.as_posix()

    def get_output_exec_path(self, serializable=False) -> "pathlib.PurePosixPath | str | None":
        """Get path for the node that is execution dependee of this node.

        Args:
            serializable (bool, optional): Return value is serializable. Defaults to False.

        Returns:
            pathlib.PurePosixPath | str | None: Execution dependee node path.
        """
        path: pathlib.PurePosixPath = self.data(
            role=Node.Roles.OUTPUT_EXEC_ROLE.value)
        if path is None or not serializable:
            return path
        return path.as_posix()

    def is_input_exec_cyclic(self, other_node: "Node | pathlib.PurePosixPath | str") -> bool:
        other_node = self.stage.node(other_node)
        return other_node.get_input_exec_path() == self.path

    def set_input_exec_path(self, path: "pathlib.PurePosixPath | str | Node", silent=False) -> None:
        """Set given node as execution dependency.

        Args:
            path (pathlib.PurePosixPath | str | Node): Node instance or path.
            silent (bool, optional): Do not notify other nodes of the change,
            and just set data. Defaults to False.

        Raises:
            TypeError: Invalid input provided.
        """
        if isinstance(path, Node):
            path = path.path
        elif isinstance(path, pathlib.PurePosixPath):
            pass
        elif isinstance(path, str):
            path = pathlib.PurePosixPath(path)
        elif path is None:
            pass
        else:
            LOGGER.error(f"{self} | Invalid input exec path: {path}")
            raise TypeError("Invalid input exec path type")

        if silent:
            self.setData(path, role=Node.Roles.INPUT_EXEC_ROLE.value)
            return

        new_input_exec_node: "Node" = self.stage.node(path)
        previous_input_exec_node = self.stage.node(self.get_input_exec_path())
        if new_input_exec_node == previous_input_exec_node:
            LOGGER.debug(f"{self} | exec output set to {path}")
            return

        if new_input_exec_node and new_input_exec_node.scope != self.scope:
            LOGGER.error(
                f"{self} | Invalid new input scope: {new_input_exec_node.scope}")
            return

        # Set connections
        if new_input_exec_node is None:
            self.setData(None, role=Node.Roles.INPUT_EXEC_ROLE.value)
        else:
            self.setData(new_input_exec_node.path,
                         role=Node.Roles.INPUT_EXEC_ROLE.value)

        # Reset old input node
        if previous_input_exec_node is not None:
            previous_input_exec_node.set_output_exec_path(None, silent=True)

        # Get path from new node to self
        # If its different from self.path -> store new path
        if new_input_exec_node is not None:
            if new_input_exec_node.get_output_exec_path() != self.path:
                new_input_exec_node.set_output_exec_path(self.path)
        self.signals.input_exec_changed.emit()

    def set_output_exec_path(self, path: "pathlib.PurePosixPath | str | Node", silent=False) -> None:
        """Set given node as execution dependee.

        Args:
            path (pathlib.PurePosixPath | str | Node): Dependee node instance or path.
            silent (bool, optional): Do not notify other nodes of the change,
            and just set data. Defaults to False.

        Raises:
            TypeError: Invalid input provided.
        """
        if isinstance(path, Node):
            path = path.path
        elif isinstance(path, pathlib.PurePosixPath):
            pass
        elif isinstance(path, str):
            path = pathlib.PurePosixPath(path)
        elif path is None:
            pass
        else:
            LOGGER.error(f"{self} | Invalid output exec path: {path}")
            raise TypeError("Invalid output exec path type")

        if silent:
            self.setData(path, role=Node.Roles.OUTPUT_EXEC_ROLE.value)
            return

        new_output_exec_node = self.stage.node(path)
        previous_output_exec_node = self.stage.node(
            self.get_output_exec_path())
        if new_output_exec_node == previous_output_exec_node:
            LOGGER.debug(f"{self} | exec output set to {path}")
            return

        if new_output_exec_node and new_output_exec_node.scope != self.scope:
            LOGGER.error(
                f"{self} | Invalid new output scope: {new_output_exec_node.scope}")
            return
        # Set connections
        if new_output_exec_node is None:
            self.setData(None, role=Node.Roles.OUTPUT_EXEC_ROLE.value)
        else:
            self.setData(new_output_exec_node.path,
                         role=Node.Roles.OUTPUT_EXEC_ROLE.value)

        # Reset old output node
        if previous_output_exec_node is not None:
            previous_output_exec_node.set_input_exec_path(None, silent=True)

        # Get path from new node to self
        # If its different from self.path -> store new path
        if new_output_exec_node is not None:
            if new_output_exec_node.get_output_exec_path() != self.path:
                new_output_exec_node.set_input_exec_path(self.path)
        self.signals.output_exec_changed.emit()

    def on_changed(self):
        pass

    def serialize(self) -> OrderedDict:
        """Serialize node to dict.

        Returns:
            OrderedDict: serialized data
        """
        data = super().serialize()
        children = [child.serialize() for child in self.list_children()]
        attribs = [attr.serialize() for _, attr in self.attribs.items()]

        data["name"] = self.text()
        data["active"] = self.is_active()
        data["position"] = self.serializable_position()
        data["path"] = self.path.as_posix()
        data["execution_start_path"] = self.get_execution_start_path(
            serializable=True)
        data["input_exec"] = self.get_input_exec_path(serializable=True)
        data["output_exec"] = self.get_output_exec_path(serializable=True)
        data["attribs"] = attribs
        data["children"] = children
        data["code"] = self.python_code
        data["comment"] = self.comment()
        return data

    def deserialize(self, data: OrderedDict, restore_id=True):
        """Deserialize node from serialized node dictionary.

        Args:
            data (OrderedDict): Node data dictionary.
            restore_id (bool, optional): Restore node uuid. Defaults to True.
        """
        super().deserialize(data, restore_id=restore_id)

        # ? Maybe use rename() ?
        if self.name != data.get("name", self.name):
            self.rename(data.get("name"))

        # self.setText(data.get("name", self.name))
        self.set_active(data.get("active", True))
        self.set_python_code(data.get("code", ""))
        self.set_input_exec_path(data.get("input_exec", ""), silent=True)
        self.set_output_exec_path(data.get("output_exec", ""), silent=True)
        self.set_execution_start_path(data.get("execution_start_path"))
        self.set_position(QtCore.QPointF(*data.get("position", [0.0, 0.0])))
        self.set_comment(data.get("comment", ""))

        self._update_pathmap_entry()

        # Attributes
        for attr_data in data.get("attribs", {}):
            attr_name = attr_data["name"]
            self.set_attr(attr_name, attr_data.get("value"))
            self[attr_name].deserialize(attr_data, restore_id=True)

        # Children
        for child_data in data.get("children", {}):
            child_node = Node(parent=self)
            child_node.deserialize(child_data, restore_id=True)

    def export_to_json(self, file_path: pathlib.Path):
        """Export node to json file.

        Args:
            file_path (pathlib.Path): json file path.
        """
        data = self.serialize()
        file_fn.write_json(file_path, data)

    def load_from_json(self, file_path: pathlib.Path, as_reference=False):
        """Load node from json file.

        Args:
            file_path (pathlib.Path): json file path.
            as_reference (bool, optional): if node should be locked. Defaults to False.
        """
        json_data = file_fn.load_json(file_path, object_pairs_hook=OrderedDict)
        self.deserialize(json_data, restore_id=False)

    def get_python_code(self) -> str:
        """Node python code.

        Returns:
            str: python code.
        """
        return self.python_code

    def set_python_code(self, code_str) -> None:
        """Set python code string.

        Args:
            code_str (str): python code.
        """
        self.setData(code_str, role=Node.Roles.PYTHON_CODE_ROLE.value)

    def resolve_python_code(self) -> str:
        pass

    def resolve(self):
        for attr in self.attribs.values():
            attr.resolve()

    def execute_code(self):
        """Execute code string."""
        exec(self.python_code, {"self": self})

    def clear_attributes_caches(self):
        """Clear all attributes caches."""
        for attr in self.attribs.values():
            attr.clear_cache()

    def cache_attributes_values(self):
        """Push current attributes values to cache."""
        for attr in self.attribs.values():
            attr.cache_current_value()

    def set_execution_start_path(self, child_path: "pathlib.PurePosixPath | str | None"):
        """Set execution start path to one of the child node's path.

        Args:
            child_path (pathlib.PurePosixPath | None): execution start node path.
        """
        if isinstance(child_path, Node):
            child_path = child_path.cached_path

        elif isinstance(child_path, str):
            child_path = pathlib.PurePosixPath(child_path)

        self.setData(
            child_path, role=Node.Roles.EXECUTION_START_PATH_ROLE.value)
        LOGGER.info(f"{self} | Set execution start path to: {child_path}")

    def get_execution_start_path(self, serializable=False) -> "pathlib.PurePosixPath | str | None":
        """Get execution start path. Can be child path or None.

        Args:
            serializable (bool, optional): get path as jsonable str or None. Defaults to False.

        Returns:
            pathlib.PurePosixPath | str | None: execution start path
        """
        path = self.data(role=Node.Roles.EXECUTION_START_PATH_ROLE.value)
        if serializable and isinstance(path, pathlib.PurePosixPath):
            path = path.as_posix()
        return path

    def build_execution_queue(self) -> "deque[pathlib.PurePosixPath]":
        """Build execution queue from given node.

        Returns:
            deque[pathlib.PurePosixPath]: Execution queue.
        """
        exec_queue = deque()
        if self.is_active():
            exec_queue.append(self.cached_path)
            child_path = self.get_execution_start_path()
            if child_path:
                child_node = self.stage.node(child_path)
                if child_node:
                    exec_queue.extend(child_node.build_execution_queue())
                else:
                    LOGGER.warning(
                        f"{self} | start path doesn't exist: {child_path}")

        output_path = self.get_output_exec_path()
        if output_path:
            output_node = self.stage.node(output_path)
            if output_node:
                exec_queue.extend(output_node.build_execution_queue())
            else:
                LOGGER.warning(
                    f"{self} | output exec path doesn't exist: {output_path} ")

        return exec_queue

    def execute(self):
        """Execute this node.

        Raises:
            err: run time exception raised during code execution.
        """
        if not self.is_active():
            return

        start_time = time.perf_counter()
        try:
            self.signals.execution_started.emit()
            self.cache_attributes_values()
            self.execute_code()
        except Exception as err:
            LOGGER.exception(f"{self} | Execution error.")
            self.signals.execution_failed.emit()
            raise err

        self.signals.execution_succeed.emit()
        total_time = time.perf_counter() - start_time
        LOGGER.info(f"Executed in {total_time:.4f}: {self.cached_path}")
