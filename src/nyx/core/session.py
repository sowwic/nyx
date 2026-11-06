import json
import logging
import pathlib
import typing

import shiboken6
from nyx_bridge.server import BridgeServer

from .layered_config import NyxConfig
from ..api.v1 import Stage
from ..static.paths import BRIDGE_ADDRESS_FILE_PATH


LOGGER = logging.getLogger(__name__)

SESSION_FILE_VERSION = 1
SESSION_FILE_SUFFIX = ".nyxsession"
BRIDGE_SERVER_NAME = "nyx"


class NyxSession:
    """Backend state shared by the editor: config, recent files, stages, bridge."""

    def __init__(self, config: NyxConfig | None = None) -> None:
        """Initialize NyxSession.

        Args:
            config (NyxConfig | None): config to use. A new one is created and
                resolved if omitted.
        """
        self._config = config or NyxConfig()
        if config is None:
            self._config.resolve()
        self._stages: list[Stage] = []
        self._bridge_server: BridgeServer | None = None

    @property
    def config(self) -> NyxConfig:
        """NyxConfig: layered config used by the session."""
        return self._config

    @property
    def bridge_server(self) -> BridgeServer | None:
        """BridgeServer | None: server external processes connect to, if started."""
        return self._bridge_server

    def start_bridge_server(self) -> BridgeServer | None:
        """Start the server external processes connect to, as the config describes.

        There is one server for all stages and clients. It writes the address file
        clients use to find it, and the file is removed when it stops. A failure is
        logged and leaves the application running without a server.

        Returns:
            BridgeServer | None: the running server, None if it is disabled or
                could not start.
        """
        values = self._config.values.bridge
        if not values.enabled:
            LOGGER.info("Bridge server is disabled in the config")
            return None
        try:
            if self._bridge_server is None:
                self._bridge_server = BridgeServer(
                    name=BRIDGE_SERVER_NAME,
                    host=values.host,
                    port=values.port,
                    token=values.token or None,
                    address_file=BRIDGE_ADDRESS_FILE_PATH,
                )
            self._bridge_server.start()
        except OSError:
            LOGGER.exception("Could not start the bridge server")
            return None
        LOGGER.info(
            "Bridge server listening on %s:%s, clients find it through %s",
            self._bridge_server.host,
            self._bridge_server.port,
            BRIDGE_ADDRESS_FILE_PATH,
        )
        return self._bridge_server

    def shutdown(self) -> None:
        """Release what the session holds on to, e.g. when the application quits."""
        if self._bridge_server is not None:
            self._bridge_server.stop()

    # Open stages
    @property
    def stages(self) -> list[Stage]:
        """list[Stage]: currently registered stages that are still alive."""
        self._stages = [s for s in self._stages if shiboken6.isValid(s)]
        return list(self._stages)

    def register_stage(self, stage: Stage) -> None:
        """Track a stage as open in this session.

        Args:
            stage (Stage): stage to register.
        """
        if stage not in self._stages:
            self._stages.append(stage)

    def unregister_stage(self, stage: Stage) -> None:
        """Stop tracking a stage.

        Args:
            stage (Stage): stage to unregister.
        """
        if stage in self._stages:
            self._stages.remove(stage)

    def find_stage_for_file(self, file_path: pathlib.Path | str) -> Stage | None:
        """Return the open stage loaded from/saved to given file, if any."""
        target = pathlib.Path(file_path).resolve()
        for stage in self.stages:
            if (
                stage.file_path is not None
                and pathlib.Path(stage.file_path).resolve() == target
            ):
                return stage
        return None

    # Recent files
    @property
    def recent_files(self) -> list[str]:
        """list[str]: recently used stage file paths, most recent first."""
        return self._config.values.editor_session.recent_files

    def add_recent_file(self, file_path: str) -> None:
        """Add a file to the top of the recent files and persist config.

        Args:
            file_path (str): stage file path. Ignored if already listed.
        """
        recent_files = self.recent_files
        if file_path in recent_files:
            return
        recent_files.insert(0, file_path)
        del recent_files[max(self._config.values.editor_session.max_recent_files, 0) :]
        self._config.save()

    def remove_recent_file(self, file_path: str) -> None:
        """Remove a file from the recent files and persist config.

        Args:
            file_path (str): stage file path.
        """
        recent_files = self.recent_files
        if file_path in recent_files:
            recent_files.remove(file_path)
            self._config.save()

    # Serialization
    def to_dict(
        self,
        stage_state: typing.Callable[[Stage], dict] | None = None,
        active_stage: Stage | None = None,
    ) -> dict:
        """Serialize the session. Stages never saved to a file are skipped.

        Args:
            stage_state: returns extra per-stage state (e.g. scope, view) to store.
            active_stage: stage to be restored as the active one.
        """
        stages = []
        for stage in self.stages:
            if not stage.file_path:
                continue
            entry = {"path": str(stage.file_path)}
            if stage_state is not None:
                entry.update(stage_state(stage))
            stages.append(entry)
        data = {"version": SESSION_FILE_VERSION, "stages": stages}
        if active_stage is not None and active_stage.file_path:
            data["active"] = str(active_stage.file_path)
        return data

    def save_to_file(
        self,
        file_path: pathlib.Path | str,
        stage_state: typing.Callable[[Stage], dict] | None = None,
        active_stage: Stage | None = None,
    ) -> None:
        """Write the session to a file.

        Args:
            file_path (pathlib.Path | str): destination file.
            stage_state (Callable[[Stage], dict] | None): returns extra per-stage state.
            active_stage (Stage | None): stage to restore as the active one.
        """
        data = self.to_dict(stage_state, active_stage)
        pathlib.Path(file_path).write_text(json.dumps(data, indent=4))

    @staticmethod
    def read_file(file_path: pathlib.Path | str) -> dict:
        """Read a session file.

        Returns:
            dict: {"active": path | None, "stages": [{"path": str, ...}, ...]}
        """
        data = json.loads(pathlib.Path(file_path).read_text())
        stages = []
        for entry in data.get("stages", []):
            # Version 1 stored plain path strings
            stages.append({"path": entry} if isinstance(entry, str) else dict(entry))
        return {"active": data.get("active"), "stages": stages}
