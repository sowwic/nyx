import logging
import pathlib
import runpy
import importlib.util
import typing

from nyx.api.v1 import NodeComponent, CoreNodeComponents, NodeComponentFlag


LOGGER = logging.getLogger(__name__)


class ScriptComponent(NodeComponent):
    DEFAULT_NAME = "script"
    EDITOR_QML = "ScriptComponentItem"

    ENTRY_POINT_SEPARATOR = ":"
    GLOBALS_NODE_REF_NAME = "nyx_node"
    GLOBALS_COMPONENT_REF_NAME = "nyx_cpnt"

    @classmethod
    def get_type_id(cls) -> str:
        return CoreNodeComponents.SCRIPT

    @classmethod
    def get_type_display_name(cls) -> str:
        return "Script"

    @classmethod
    def get_type_icon(cls) -> str:
        return ":/core/icons/script_cpnt"

    @classmethod
    def get_type_default_value(cls) -> str:
        return ""

    @classmethod
    def get_tags(self) -> set[str]:
        return {"common", "script", "logic"}

    @classmethod
    def get_type_default_flags(cls) -> NodeComponentFlag:
        return NodeComponentFlag.EDITABLE

    @classmethod
    def get_default_expanded_state(cls) -> bool:
        return True

    def execute(self):
        script_value = self.pull_value()
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
        return {
            self.GLOBALS_NODE_REF_NAME: self.node,
            self.GLOBALS_COMPONENT_REF_NAME: self,
        }

    def run_as_script_path(self, script_path: str | pathlib.Path) -> bool:
        file_path = pathlib.Path(script_path)
        if file_path.is_file():
            runpy.run_path(script_path, init_globals=self.build_globals())
            return True
        return False

    def run_as_module_entry_point(self, entry_point_path: str) -> bool:
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
