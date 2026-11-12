import threading
import time

import pytest
from PySide6 import QtCore

from nyx.api.v1 import CoreNodes, NodeExecutionStatus, Stage
from nyx.core.exceptions import StageExecutionCancelled
from stage_helpers import create_node


@pytest.fixture
def stage_crawler(qapp):
    stage = Stage()
    yield stage.crawler
    stage.deleteLater()


def test_wait_for_returns_the_result(stage_crawler):
    assert stage_crawler.wait_for(lambda a, b=0: a + b, 1, b=2) == 3


def test_wait_for_raises_what_the_function_raised(stage_crawler):
    def fail():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        stage_crawler.wait_for(fail)


def test_events_are_processed_while_waiting(stage_crawler):
    ticks = []
    timer = QtCore.QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()

    stage_crawler.wait_for(time.sleep, 0.3)
    timer.stop()

    assert len(ticks) >= 3


def test_cancel_ends_a_long_wait_quickly(stage_crawler):
    release = threading.Event()
    QtCore.QTimer.singleShot(100, stage_crawler.request_cancel)

    started = time.monotonic()
    with pytest.raises(StageExecutionCancelled):
        stage_crawler.wait_for(release.wait, 5)
    release.set()

    assert time.monotonic() - started < 1.5


def test_process_events_raises_only_when_cancel_was_requested(stage_crawler):
    stage_crawler.process_events()
    stage_crawler.request_cancel()

    stage_crawler.process_events(check_cancel=False)
    with pytest.raises(StageExecutionCancelled):
        stage_crawler.process_events(force=True)


def test_a_cancelled_run_ends_quietly_and_the_next_one_runs(stage_crawler):
    stage = stage_crawler.stage
    create_node(stage, CoreNodes.FLOW_START)
    cancelled, finished = [], []
    stage.execution_cancelled.connect(lambda: cancelled.append(True))
    stage.execution_finished.connect(lambda: finished.append(True))
    stage_crawler.request_cancel()
    # The flag of an earlier request must not leak into the next run.
    stage_crawler.start()
    assert not cancelled and finished == [True]

    class Cancelling:
        pass

    node = stage.root_node.find_flow_start_node()
    original = node.execute

    def execute():
        stage_crawler.request_cancel()
        stage_crawler.process_events()

    node.execute = execute
    stage_crawler.start()
    node.execute = original

    assert cancelled == [True]
    assert finished == [True]
    assert node.execution_status is NodeExecutionStatus.NOT_RAN
    assert not stage_crawler.is_running
    stage_crawler.start()
    assert finished == [True, True]


def test_start_while_running_is_refused(stage_crawler):
    stage = stage_crawler.stage
    create_node(stage, CoreNodes.FLOW_START)
    node = stage.root_node.find_flow_start_node()
    runs = []

    def execute():
        runs.append(1)
        stage_crawler.start()

    node.execute = execute
    stage_crawler.start()

    assert runs == [1]
