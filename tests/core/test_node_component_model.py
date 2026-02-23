import pathlib
import logging

from nyx.core import Stage
from nyx.core import Node
from collections import OrderedDict

LOGGER = logging.getLogger(__name__)


def test_node_components_model_serialize(output_dir: pathlib.Path):
    export_path = (
        output_dir / f"test_node_component_model_serialize{Stage.FILE_EXTENSION}"
    )
    stage = Stage()
    node = Node()
    stage.add_node(node)
    stage.export_json(export_path)

    expected_data = OrderedDict()
    expected_data["components"] = []
    serialized_model = node._components_model.serialize()
    assert serialized_model == expected_data
