import logging
import typing

from nyx_bridge.server import ClientSession

from nyx.api.v1 import (
    Node,
    CoreNodes,
    CoreNodeComponents,
    CoreDatatypes,
)


LOGGER = logging.getLogger(__name__)


class RemoteActionNode(Node):
    """Flow node running a script in the client of the enclosing Remote Client.

    The script is a python file or a "module:function" entry point, see
    `RemoteScriptComponent`. A file sees the entries of `args` as variables and hands
    data back by assigning `result`, which ends up in `response`. An entry point gets
    the entries as keyword arguments and its return value is the `result`. Everything
    has to be JSON data, anything else arrives as its `repr`.

    Subclasses add their own components and override `build_script`, `build_args` and
    `handle_response`, they don't need to touch `execute`.
    """

    DEFAULT_NAME = "remote_action"
    DEFAULT_TIMEOUT = 30.0

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.REMOTE_ACTION

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Remote Action"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/remote_action"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return (
            "Runs code in the external process of the Remote Client it is inside "
            "of and outputs the value the code assigned to `result`."
        )

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"bridge", "script"}

    def setup(self) -> None:
        """Add the flow, the script, its arguments and the response."""
        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.name = "flow"
        self.flow_cpnt.readable = True
        self.flow_cpnt.writable = True

        self.script_cpnt = self.components_model.create_component(
            CoreNodeComponents.REMOTE_SCRIPT
        )
        self.script_cpnt.name = "script"
        self.script_cpnt.description = (
            "Python file or module:function entry point to run in the client. "
            "Assign the value to send back to `result`."
        )
        self.script_cpnt.writable = True

        self.args_cpnt = self.components_model.create_component(CoreNodeComponents.VALUE)
        self.args_cpnt.name = "args"
        self.args_cpnt.description = "Variables the script can use, by name."
        self.args_cpnt.is_editable = True
        self.args_cpnt.writable = True
        self.args_cpnt.set_datatype(CoreDatatypes.DICT)
        self.args_cpnt.push_value({})

        self.timeout_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.timeout_cpnt.name = "timeout"
        self.timeout_cpnt.description = (
            "Seconds to wait for the answer before failing. 0 or less waits forever."
        )
        self.timeout_cpnt.is_editable = True
        self.timeout_cpnt.writable = True
        self.timeout_cpnt.set_datatype(CoreDatatypes.FLOAT)
        self.timeout_cpnt.push_value(self.DEFAULT_TIMEOUT)

        self.response_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.response_cpnt.name = "response"
        self.response_cpnt.description = "Value the script assigned to `result`."
        self.response_cpnt.readable = True
        self.response_cpnt.is_editable = False
        self.response_cpnt.set_datatype(CoreDatatypes.OBJECT)

        self.components_model.add_component(self.flow_cpnt)
        self.components_model.add_component(self.script_cpnt)
        self.components_model.add_component(self.args_cpnt)
        self.components_model.add_component(self.timeout_cpnt)
        self.components_model.add_component(self.response_cpnt)

    def build_script(self, args: dict[str, typing.Any]) -> str:
        """Get the code to run. Override in subclasses.

        Args:
            args (dict[str, Any]): the variables the code will see.

        Returns:
            str: source code.
        """
        return self.script_cpnt.build_code(args)

    def build_args(self) -> dict[str, typing.Any]:
        """Get the variables the code sees. Override in subclasses.

        Returns:
            dict[str, Any]: JSON serializable values by name.
        """
        return dict(self.args_cpnt.pull_value() or {})

    def handle_response(self, response: typing.Any) -> None:
        """Take what the code answered. Override in subclasses.

        Args:
            response (Any): value the code assigned to `result`.
        """
        # Not evaluated: the response is stored as it came
        self.response_cpnt.push_value(response, evaluate=False)

    def execute(self) -> None:
        """Run the code in the client and handle the response.

        Raises:
            LookupError: the node is not inside a Remote Client.
            RemoteExecutionError: the code raised in the client.
            TimeoutError: no answer in time.
            ClientDisconnected: the client went away.
        """
        session = self.stage.crawler.context.require(ClientSession)
        timeout = self.timeout_cpnt.pull_value()
        # The code and the arguments are built before anything is sent, so a problem
        # in them doesn't leave a half done request behind.
        args = self.build_args()
        result = self.stage.crawler.wait_for(
            session.execute,
            self.build_script(args),
            args=args,
            timeout=timeout if timeout and timeout > 0 else None,
        )
        if result.stdout:
            LOGGER.info("%s | stdout:\n%s", self.path, result.stdout.rstrip())
        if result.stderr:
            LOGGER.warning("%s | stderr:\n%s", self.path, result.stderr.rstrip())
        self.handle_response(result.value)
