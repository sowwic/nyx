import pathlib
from nyx.utils import logging_fn


def test_main_logger(output_dir: pathlib.Path):
    logger = logging_fn.get_main_logger()
    assert logger.name == "nyx"
