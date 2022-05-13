import pathlib
import dataclasses

from nyx import get_main_logger
from nyx.utils import file_fn

LOGGER = get_main_logger()
CONFIG_FILE_PATH = file_fn.get_nyx_data_dir() / "config.json"


@dataclasses.dataclass
class Config:
    window_size: "tuple[int]" = (600, 400)
    window_position: "tuple[int]" = tuple()
    window_always_on_top: bool = True
    logging_level: int = 10
    maya_port: int = 7221
    dark_mode: bool = True

    @classmethod
    def get_fields_names(cls):
        """Get available config field names.

        Returns:
            set: set of existing field names
        """
        return set(each_field.name for each_field in dataclasses.fields(cls))

    @classmethod
    def _load_from_json(cls, file_path: pathlib.Path):
        """Create Config instance from given json file.

        Args:
            file_path (pathlib.Path): path to json file

        Returns:
            Config: new instance
        """
        json_data = file_fn.load_json(file_path)
        field_names = cls.get_fields_names()
        for json_field_name in list(json_data.keys()):
            if json_field_name not in field_names:
                json_data.pop(json_field_name)
                LOGGER.warning(f"Unused config field name: {json_field_name}")
        LOGGER.info(f"Loaded config: {CONFIG_FILE_PATH}")
        return cls(**json_data)

    @classmethod
    def reset(cls):
        """Write default config values to file.

        Returns:
            Config: default config instance
        """
        instance = cls()
        CONFIG_FILE_PATH.parent.mkdir(exist_ok=True)
        file_fn.write_json(CONFIG_FILE_PATH, dataclasses.asdict(instance))
        LOGGER.info("Config reset")
        return instance

    @classmethod
    def load(cls):
        """Load config from CONFIG_FILE_PATH

        Returns:
            Config: new instance
        """
        CONFIG_FILE_PATH.parent.mkdir(exist_ok=True)
        if not CONFIG_FILE_PATH.is_file():
            return cls.reset()
        return cls._load_from_json(CONFIG_FILE_PATH)

    def save(self):
        """Write config to json file."""
        CONFIG_FILE_PATH.parent.mkdir(exist_ok=True)
        file_fn.write_json(CONFIG_FILE_PATH, dataclasses.asdict(self))
        LOGGER.info(f"Saved config: {CONFIG_FILE_PATH}")
