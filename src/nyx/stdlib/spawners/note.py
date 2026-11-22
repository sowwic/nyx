from nyx.api.v1 import CoreSpawners, CoreUtilObjects
from nyx.api.v1.editor_utils import UtilObjectSpawner


class NoteSpawner(UtilObjectSpawner):
    """Creates a note where the user clicked."""

    @classmethod
    def get_type_id(cls) -> str:
        """str: id of the spawner."""
        return CoreSpawners.NOTE

    @classmethod
    def get_util_object_type_id(cls) -> str:
        """str: type id of the util object created."""
        return CoreUtilObjects.NOTE
