import logging
from collections import deque

from nyx.core import Node, Stage
from nyx.api.v1 import Node, Stage, commands

LOGGER = logging.getLogger(__name__)


def test_crawler_order_correct_with_flat_hierarchy():
    stage = Stage()

    flow_create_command = commands.CreateNodeCommand(
        stage=stage, node_type_id="core:flow_start"
    )
    stage.push_command(flow_create_command)
    flow_start_node = stage.node(flow_create_command.node_path)
    stage.crawler.start()
    assert stage.crawler.visited_node_paths == [flow_start_node.path.as_posix()]
