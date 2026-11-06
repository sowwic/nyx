from PySide6 import QtCore


class BridgeEvents(QtCore.QObject):
    """Qt signals for what happens to the bridge server.

    The server tells its listeners from its own threads. The signals are emitted from
    there too, and Qt delivers them to slots of the main thread on its event loop, so
    widgets can connect to them directly.

    Attributes:
        started: emitted when the server is listening
        stopped: emitted when the server has stopped
        clients_changed: emitted when a client has connected or gone
    """

    started = QtCore.Signal()
    stopped = QtCore.Signal()
    clients_changed = QtCore.Signal()

    def on_server_started(self, server) -> None:
        """Listener of the server, see `BridgeServer.add_listener`."""
        self.started.emit()

    def on_server_stopped(self, server) -> None:
        """Listener of the server, see `BridgeServer.add_listener`."""
        self.stopped.emit()
        self.clients_changed.emit()

    def on_client_connected(self, server, session) -> None:
        """Listener of the server, see `BridgeServer.add_listener`."""
        self.clients_changed.emit()

    def on_client_disconnected(self, server, session) -> None:
        """Listener of the server, see `BridgeServer.add_listener`."""
        self.clients_changed.emit()
