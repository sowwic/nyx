import collections.abc
import pathlib
import re

from nyx.api.v1 import CoreNodeComponents

from .script import ScriptComponent


ENTRY_POINT_RESOLVER = """\
def _nyx_entry_point(path, name):
    import importlib

    parts = path.split(".")
    for count in range(len(parts), 0, -1):
        module_name = ".".join(parts[:count])
        try:
            target = importlib.import_module(module_name)
        except ModuleNotFoundError as err:
            # Go on only when the module itself, or a package above it, is missing:
            # not when it exists and imports something that is not there.
            missing = err.name or ""
            if module_name != missing and not module_name.startswith(missing + "."):
                raise
            continue
        for attribute in parts[count:]:
            target = getattr(target, attribute)
        return getattr(target, name)
    raise ModuleNotFoundError(f"No module named {parts[0]!r}", name=parts[0])
"""
"""str: code defining `_nyx_entry_point(path, name)` in the client.

It imports the longest importable start of a dotted path and reads the rest as
attributes, so a path like `bpy.ops.mesh` works although `mesh` is not a module.
"""


class RemoteScriptComponent(ScriptComponent):
    """Component naming a script that runs in an external process.

    Takes the same values as `ScriptComponent`, a script path or a "module:function"
    entry point, but doesn't run anything when the node executes: the node sends the
    code built by `build_code` to the client.
    """

    ENTRY_POINT_PATTERN = re.compile(r"^[A-Za-z_][\w.]*:[A-Za-z_]\w*$")

    @classmethod
    def get_type_id(cls) -> str:
        """str: component type id."""
        return CoreNodeComponents.REMOTE_SCRIPT

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Remote Script"

    @classmethod
    def get_description(cls) -> str:
        """str: what the component type does, shown in the palette."""
        return (
            "Names a python file or a module entry point to run in an external "
            "process, instead of in the application."
        )

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: component tags."""
        return {"script", "bridge"}

    def execute(self):
        """Do nothing, the script runs in the client."""

    def build_code(self, argument_names: collections.abc.Iterable[str] = ()) -> str:
        """Build the code the client runs.

        A file is sent as its source, read here, so the client doesn't need to see it.
        An entry point is imported and called in the client, with the arguments passed
        as keyword arguments and its return value as `result`. The module has to be
        importable there. The part before the colon can go through attributes of a
        module, like `os.path:join` or `bpy.ops.mesh:primitive_cube_add`.

        Args:
            argument_names (Iterable[str]): names of the variables the client has,
                the arguments of an entry point.

        Raises:
            ValueError: the value is empty, or neither a file nor an entry point.

        Returns:
            str: source code.
        """
        value = self.cast_value(self.pull_value())
        if not value:
            raise ValueError(f"{self.name}: No script path or entry point set")

        file_path = pathlib.Path(value)
        if file_path.is_file():
            return file_path.read_text(encoding="utf-8")

        if self.ENTRY_POINT_PATTERN.match(value):
            module_name, function_name = value.split(self.ENTRY_POINT_SEPARATOR)
            return (
                f"{ENTRY_POINT_RESOLVER}"
                f"result = _nyx_entry_point({module_name!r}, {function_name!r})"
                f"(**{{name: globals()[name] for name in {list(argument_names)!r}}})\n"
            )

        raise ValueError(
            f"{self.name}: Provided value is not script path "
            f"or module entry point path: {value}"
        )
