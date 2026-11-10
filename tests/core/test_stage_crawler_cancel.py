import threading
import time

import pytest
from PySide6 import QtCore

from nyx.api.v1 import CoreNodes, NodeExecutionStatus, Stage, commands
from nyx.core.exceptions import StageExecutionCancelled


def create(stage, type_id, parent=None, name=None):
    command = commands.CreateNodeCommand(
        stage=stage, type_id=type_id, parent_node=parent, name=name
    )
    stage.push_command(command)
    return command.result_node


@pytest.fixture
def crawler(qapp):
    stage = Stage()
    yield stage.crawler
    stage.deleteLater()


def test_wait_for_returns_the_result(crawler):
    assert crawler.wait_for(lambda a, b=0: a + b, 1, b=2) == 3


def test_wait_for_raises_what_the_function_raised(crawler):
    def fail():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        crawler.wait_for(fail)


def test_events_are_processed_while_waiting(crawler):
    ticks = []
    timer = QtCore.QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()

    crawler.wait_for(time.sleep, 0.3)
    timer.stop()

    assert len(ticks) >= 3


def test_cancel_ends_a_long_wait_quickly(crawler):
    release = threading.Event()
    QtCore.QTimer.singleShot(100, crawler.request_cancel)

    started = time.monotonic()
    with pytest.raises(StageExecutionCancelled):
        crawler.wait_for(release.wait, 5)
    release.set()

    assert time.monotonic() - started < 1.5


def test_process_events_raises_only_when_cancel_was_requested(crawler):
    crawler.process_events()
    crawler.request_cancel()

    crawler.process_events(check_cancel=False)
    with pytest.raises(StageExecutionCancelled):
        crawler.process_events(force=True)


def test_a_cancelled_run_ends_quietly_and_the_next_one_runs(crawler):
    stage = crawler.stage
    create(stage, CoreNodes.FLOW_START)
    cancelled, finished = [], []
    stage.execution_cancelled.connect(lambda: cancelled.append(True))
    stage.execution_finished.connect(lambda: finished.append(True))
    crawler.request_cancel()
    # The flag of an earlier request must not leak into the next run.
    crawler.start()
    assert not cancelled and finished == [True]

    class Cancelling:
        pass

    node = stage.root_node.find_flow_start_node()
    original = node.execute

    def execute():
        crawler.request_cancel()
        crawler.process_events()

    node.execute = execute
    crawler.start()
    node.execute = original

    assert cancelled == [True]
    assert finished == [True]
    assert node.execution_status is NodeExecutionStatus.NOT_RAN
    assert not crawler.is_running
    crawler.start()
    assert finished == [True, True]


def test_start_while_running_is_refused(crawler):
    stage = crawler.stage
    create(stage, CoreNodes.FLOW_START)
    node = stage.root_node.find_flow_start_node()
    runs = []

    def execute():
        runs.append(1)
        crawler.start()

    node.execute = execute
    crawler.start()

    assert runs == [1]
