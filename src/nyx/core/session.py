import json
import pathlib
import typing

import shiboken6

from .layered_config import MAX_RECENT_FILES, NyxConfig
from ..api.v1 import Stage


SESSION_FILE_VERSION = 1
SESSION_FILE_SUFFIX = ".nyxsession"


class NyxSession:
    """Backend state shared by the editor: config, recent files and open stages."""

    def __init__(self, config: NyxConfig | None = None) -> None:
        self._config = config or NyxConfig()
        if config is None:
            self._config.resolve()
        self._stages: list[Stage] = []

    @property
    def config(self) -> NyxConfig:
        return self._config

    # Open stages
    @property
    def stages(self) -> list[Stage]:
        self._stages = [s for s in self._stages if shiboken6.isValid(s)]
        return list(self._stages)

    def register_stage(self, stage: Stage) -> None:
        if stage not in self._stages:
            self._stages.append(stage)

    def unregister_stage(self, stage: Stage) -> None:
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
        return self._config.values.editor_session.recent_files

    def add_recent_file(self, file_path: str) -> None:
        recent_files = self.recent_files
        if file_path in recent_files:
            return
        recent_files.insert(0, file_path)
        del recent_files[MAX_RECENT_FILES:]
        self._config.save()

    def remove_recent_file(self, file_path: str) -> None:
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
