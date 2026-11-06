from PySide6 import QtCore

from nyx_bridge.server import ClientSession

from nyx.api.v1 import (
    Node,
    NodeExecutionContext,
    CoreNodes,
    CoreNodeComponents,
    CoreDatatypes,
)


class RemoteClientNode(Node):
    """Node connecting its children to a client of a bridge server.

    Waits for a matching external process to be connected to the
    bridge server of the application, then lets the nodes inside of it send code to
    that process, see `RemoteActionNode`.
    """

    DEFAULT_NAME = "remote_client"
    DEFAULT_TIMEOUT = 30.0

    @classmethod
    def get_type_id(cls) -> str:
        """str: node type id."""
        return CoreNodes.REMOTE_CLIENT

    @classmethod
    def get_type_display_name(cls) -> str:
        """str: name shown in the UI."""
        return "Remote Client"

    @classmethod
    def get_type_icon(cls) -> str:
        """str: resource path of the type icon."""
        return ":/icons/remote_client"

    @classmethod
    def get_description(cls) -> str:
        """str: what the node type does, shown in the palette."""
        return (
            "Waits for an external process to connect to the server, and lets the nodes "
            "inside of it run code in that process."
        )

    @classmethod
    def get_tags(cls) -> set[str]:
        """set[str]: node tags."""
        return {"bridge", "scope"}

    def setup(self) -> None:
        """Add the flow, the inputs selecting the client and the client name output."""
        self._client_session: ClientSession | None = None

        self.flow_cpnt = self.components_model.create_component(CoreNodeComponents.FLOW)
        self.flow_cpnt.name = "flow"
        self.flow_cpnt.readable = True
        self.flow_cpnt.writable = True

        self.client_name_cpnt = self._create_input(
            "client_name",
            "Name of the client to wait for. Empty accepts any.",
            CoreDatatypes.STRING,
            "",
        )
        self.client_kind_cpnt = self._create_input(
            "client_kind",
            "Kind of the client to wait for, as it reports itself. Empty accepts any.",
            CoreDatatypes.STRING,
            "",
        )
        self.timeout_cpnt = self._create_input(
            "timeout",
            "Seconds to wait for the client before failing. 0 or less waits forever.",
            CoreDatatypes.FLOAT,
            self.DEFAULT_TIMEOUT,
        )

        self.client_cpnt = self.components_model.create_component(
            CoreNodeComponents.VALUE
        )
        self.client_cpnt.name = "client"
        self.client_cpnt.description = "Name of the connected client."
        self.client_cpnt.readable = True
        self.client_cpnt.is_editable = False
        self.client_cpnt.set_datatype(CoreDatatypes.STRING)

        self.components_model.add_component(self.flow_cpnt)
        for component in (
            self.client_name_cpnt,
            self.client_kind_cpnt,
            self.timeout_cpnt,
            self.client_cpnt,
        ):
            self.components_model.add_component(component)

    def _create_input(self, name: str, description: str, datatype: str, default):
        """Create an editable input value component.

        Args:
            name (str): component name.
            description (str): component description.
            datatype (str): datatype id.
            default (Any): initial value.

        Returns:
            NodeComponent: new component, not added to the node yet.
        """
        component = self.components_model.create_component(CoreNodeComponents.VALUE)
        component.name = name
        component.description = description
        component.is_editable = True
        component.writable = True
        component.set_datatype(datatype)
        component.push_value(default)
        return component

    def pre_execution_hook(self) -> None:
        """Forget the client of the previous run."""
        self._client_session = None
        self.client_cpnt.push_value("", evaluate=False)

    def execute(self) -> None:
        """Wait for the client.

        Raises:
            RuntimeError: the bridge server is not running.
            TimeoutError: no matching client connected in time.
        """
        session = getattr(QtCore.QCoreApplication.instance(), "session", None)
        server = session.bridge_server if session is not None else None
        if server is None or not server.is_running:
            raise RuntimeError("The bridge server is not running")
        timeout = self.timeout_cpnt.pull_value()
        try:
            self._client_session = server.wait_for_client(
                name=self.client_name_cpnt.pull_value() or None,
                kind=self.client_kind_cpnt.pull_value() or None,
                timeout=timeout if timeout and timeout > 0 else None,
            )
        except TimeoutError as err:
            raise TimeoutError(
                f"No matching client connected to {server.host}:{server.port} within "
                f"{timeout}s"
            ) from err
        self.client_cpnt.push_value(self._client_session.name, evaluate=False)

    def enter_scope(self, context: NodeExecutionContext) -> None:
        """Provide the client to the nodes inside.

        Args:
            context (NodeExecutionContext): context of the crawl.
        """
        if self._client_session is not None:
            context.provide(self._client_session)
