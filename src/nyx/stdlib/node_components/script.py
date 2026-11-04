import logging
import pathlib
import runpy
import importlib.util
import typing

from nyx.api.v1 import (
    NodeComponent,
    CoreNodeComponents,
    NodeComponentFlag,
    CoreDatatypes,
    LiteralValueStorage,
)


LOGGER = logging.getLogger(__name__)


class ScriptComponent(NodeComponent):
    """Component running a python file or a module entry point when executed.

    The script gets the node and the component as globals. The value is a path, so it
    is kept as typed and never evaluated as an expression.
    """

    VALUE_STORAGE_CLS = LiteralValueStorage

    DEFAULT_NAME = "script"
    EDITOR_QML = "ScriptComponentItem"

    ENTRY_POINT_SEPARATOR = ":"
    GLOBALS_NODE_REF_NAME = "nyx_node"
    GLOBALS_COMPONENT_REF_NAME = "nyx_cpnt"

    @classmethod
    def get_type_id(cls) -> str:
        """str: component type id."""
        return CoreNodeComponents.SCRIPT

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Script"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/core/icons/script_cpnt"

    @classmethod
    def get_type_default_value(cls) -> str:
        """str: empty script path."""
        return ""

    @classmethod
    def get_type_default_datatype(cls) -> str:
        """str: the value is a script path or an entry point, both strings."""
        return CoreDatatypes.STRING

    @classmethod
    def get_description(cls) -> str:
        """str: what the component type does, shown in the palette."""
        return "Runs a python file or a module entry point when the node executes."

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: component tags."""
        return {"common", "script", "logic"}

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        """NodeComponentFlag: editable."""
        return NodeComponentFlag.EDITABLE

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        """bool: script components start expanded."""
        return True

    def execute(self):
        """Run the value as a script path or a module entry point.

        Raises:
            ValueError: if the value is neither.
            DatatypeCastError: if the pulled value can't be used as a string.
        """
        script_value = self.cast_value(self.pull_value())
        if not script_value:
            return

        ran_as_module = False
        ran_as_file = self.run_as_script_path(script_path=script_value)
        if not ran_as_file:
            ran_as_module = self.run_as_module_entry_point(entry_point_path=script_value)

        if not (ran_as_file or ran_as_module):
            raise ValueError(
                f"{self.name}: Provided value is not script path "
                f"or module entry point path: {script_value}"
            )

    def build_globals(self):
        """Build the globals passed to the script.

        Returns:
            dict: the node and the component under their reference names.
        """
        return {
            self.GLOBALS_NODE_REF_NAME: self.node,
            self.GLOBALS_COMPONENT_REF_NAME: self,
        }

    def run_as_script_path(self, script_path: str | pathlib.Path) -> bool:
        """Run a python file.

        Args:
            script_path (str | pathlib.Path): file to run.

        Returns:
            bool: file exists and was run.
        """
        file_path = pathlib.Path(script_path)
        if file_path.is_file():
            runpy.run_path(script_path, init_globals=self.build_globals())
            return True
        return False

    def run_as_module_entry_point(self, entry_point_path: str) -> bool:
        """Run a function of an importable module.

        Args:
            entry_point_path (str): "module:function" path.

        Returns:
            bool: module was found and the function was called.

        Raises:
            ValueError: if the module has no such function.
        """
        module_name, entry_point = entry_point_path.split(self.ENTRY_POINT_SEPARATOR)
        found_module = importlib.util.find_spec(name=module_name) is not None
        if not found_module:
            return False

        module_namespace = runpy.run_module(
            module_name,
            init_globals=self.build_globals(),
        )
        entry_point_func: typing.Callable | None = module_namespace.get(entry_point)
        if entry_point_func is None:
            raise ValueError(f"Failed to find entry point: {entry_point_path}")

        entry_point_func()
        return True
