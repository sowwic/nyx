import logging
import pathlib
from collections import OrderedDict

import pytest
from nyx.core import Node, Stage

LOGGER = logging.getLogger(__name__)


def test_node_components_model_serialize(
    output_dir: pathlib.Path, request: pytest.FixtureRequest
):
    export_path = output_dir / f"{request.node.name}{Stage.FILE_EXTENSION}"
    stage = Stage()
    node = Node()
    stage.add_node(node)
    stage.export_json(export_path)

    expected_data = OrderedDict()
    expected_data["components"] = []
    serialized_model = node._components_model.serialize()
    assert serialized_model == expected_data
