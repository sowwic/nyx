from __future__ import annotations

import typing

from PySide6 import QtCore, QtGui, QtWidgets

if typing.TYPE_CHECKING:
    from nyx.core.session import NyxSession


class BridgePanel(QtWidgets.QWidget):
    """Shows the bridge server and the external processes connected to it.

    Lets the user start and stop the server and copy what a client needs to connect.
    """

    CLIENT_COLUMNS = ("Name", "Kind", "Version", "Id")
    HIDDEN_TOKEN_TEXT = "••••••••"

    def __init__(
        self, session: NyxSession, parent: QtWidgets.QWidget | None = None
    ) -> None:
        """Initialize BridgePanel.

        Args:
            session (NyxSession): session owning the bridge server.
            parent (QtWidgets.QWidget | None): parent widget.
        """
        super().__init__(parent)
        self._session = session

        self.status_label = QtWidgets.QLabel(self)
        self.toggle_button = QtWidgets.QPushButton(self)
        self.address_label = QtWidgets.QLabel(self)
        self.copy_address_button = QtWidgets.QPushButton("Copy", self)
        self.token_label = QtWidgets.QLabel(self)
        self.show_token_button = QtWidgets.QPushButton("Show", self)
        self.show_token_button.setCheckable(True)
        self.copy_token_button = QtWidgets.QPushButton("Copy", self)
        self.clients_table = QtWidgets.QTableWidget(0, len(self.CLIENT_COLUMNS), self)
        self.clients_table.setHorizontalHeaderLabels(list(self.CLIENT_COLUMNS))
        self.clients_table.verticalHeader().setVisible(False)
        self.clients_table.horizontalHeader().setStretchLastSection(True)
        self.clients_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.clients_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )

        for label in (self.address_label, self.token_label):
            label.setTextInteractionFlags(
                QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
            )

        grid = QtWidgets.QGridLayout()
        grid.addWidget(QtWidgets.QLabel("Status"), 0, 0)
        grid.addWidget(self.status_label, 0, 1)
        grid.addWidget(self.toggle_button, 0, 2, 1, 2)
        grid.addWidget(QtWidgets.QLabel("Address"), 1, 0)
        grid.addWidget(self.address_label, 1, 1)
        grid.addWidget(self.copy_address_button, 1, 2, 1, 2)
        grid.addWidget(QtWidgets.QLabel("Token"), 2, 0)
        grid.addWidget(self.token_label, 2, 1)
        grid.addWidget(self.show_token_button, 2, 2)
        grid.addWidget(self.copy_token_button, 2, 3)
        grid.setColumnStretch(1, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addWidget(QtWidgets.QLabel("Connected clients"))
        layout.addWidget(self.clients_table)

        events = session.bridge_events
        events.started.connect(self.refresh)
        events.stopped.connect(self.refresh)
        events.clients_changed.connect(self.refresh)
        self.toggle_button.clicked.connect(self.toggle_server)
        self.copy_address_button.clicked.connect(self.copy_address)
        self.copy_token_button.clicked.connect(self.copy_token)
        self.show_token_button.toggled.connect(self.refresh)

        self.refresh()

    def toggle_server(self) -> None:
        """Stop the server if it is running, start it otherwise."""
        server = self._session.bridge_server
        if server is not None and server.is_running:
            self._session.stop_bridge_server()
        else:
            self._session.start_bridge_server()
        self.refresh()

    def copy_address(self) -> None:
        """Copy `host:port` of the running server to the clipboard."""
        server = self._session.bridge_server
        if server is not None and server.is_running:
            QtGui.QGuiApplication.clipboard().setText(f"{server.host}:{server.port}")

    def copy_token(self) -> None:
        """Copy the token of the server to the clipboard."""
        server = self._session.bridge_server
        if server is not None:
            QtGui.QGuiApplication.clipboard().setText(server.token)

    def refresh(self) -> None:
        """Show the current state of the server and its clients."""
        server = self._session.bridge_server
        running = server is not None and server.is_running

        self.status_label.setText("Running" if running else "Stopped")
        self.toggle_button.setText("Stop" if running else "Start")
        self.address_label.setText(f"{server.host}:{server.port}" if running else "-")
        self.copy_address_button.setEnabled(running)

        has_token = server is not None
        if not has_token:
            self.token_label.setText("-")
        elif self.show_token_button.isChecked():
            self.token_label.setText(server.token)
        else:
            self.token_label.setText(self.HIDDEN_TOKEN_TEXT)
        self.show_token_button.setEnabled(has_token)
        self.copy_token_button.setEnabled(has_token)

        clients = server.clients if running else []
        self.clients_table.setRowCount(len(clients))
        for row, client in enumerate(clients):
            values = (client.name, client.kind, client.version, client.id)
            for column, value in enumerate(values):
                self.clients_table.setItem(
                    row, column, QtWidgets.QTableWidgetItem(str(value))
                )
