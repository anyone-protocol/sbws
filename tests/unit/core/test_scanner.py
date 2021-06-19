"""Unit tests for scanner.py."""
import concurrent.futures
import logging

import pytest
from freezegun import freeze_time

from sbws.core import scanner
from sbws.lib.circuitbuilder import CircuitBuilder
from sbws.lib.destination import DestinationList
from sbws.lib.heartbeat import Heartbeat
from sbws.lib.relayprioritizer import RelayPrioritizer

log = logging.getLogger(__name__)


def test_result_putter(sbwshome_only_datadir, result_success, rd, end_event):
    if rd is None:
        pytest.skip("ResultDump is None")
    # Put one item in the queue
    scanner.result_putter(rd, result_success)
    assert rd.queue.qsize() == 1

    # Make queue maxsize 1, so that it'll be full after the first callback.
    # The second callback will wait 1 second, then the queue will be empty
    # again.
    rd.queue.maxsize = 1
    scanner.result_putter(rd, result_success)
    # after putting 1 result, the queue will be full
    assert rd.queue.qsize() == 1
    assert rd.queue.full()
    # it's still possible to put another results, because the callback will
    # wait 1 second and the queue will be empty again.
    scanner.result_putter(rd, result_success)
    assert rd.queue.qsize() == 1
    assert rd.queue.full()
    end_event.set()


def test_complete_measurements(
    args,
    conf,
    sbwshome_only_datadir,
    controller,
    relay_list,
    result_dump,
    rd,
    mocker,
):
    """
    Test that the ``ThreadPoolExecutor``` creates the epexted number of
    futures, ``wait_for_results``process all of them and ``force_get_results``
    completes them if they were not already completed by the time
    ``wait_for_results`` has already processed them.
    There are not real measurements done and the ``results`` are None objects.
    Running the scanner with the test network, test the real measurements.

    """
    with freeze_time("2020-02-29 10:00:00"):
        hbeat = Heartbeat(conf.getpath("paths", "state_fname"))
        # rl = RelayList(args, conf, controller, measurements_period, state)
        circuit_builder = CircuitBuilder(args, conf, controller, relay_list)
        # rd = ResultDump(args, conf)
        relay_prioritizer = RelayPrioritizer(args, conf, relay_list, rd)
        destinations, error_msg = DestinationList.from_config(
            conf, circuit_builder, relay_list, controller
        )
        num_threads = conf.getint("scanner", "measurement_threads")

        mocker.patch(
            "sbws.lib.destination.DestinationList.functional_destinations",
            side_effect=[d for d in destinations._all_dests],
        )
        print("start threads")
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=num_threads, thread_name_prefix="measurer"
        ) as executor:
            pending_results = {
                executor.submit(
                    scanner.dispatch_worker_thread,
                    args,
                    conf,
                    destinations,
                    circuit_builder,
                    relay_list,
                    target,
                ): target
                for target in relay_prioritizer.best_priority()
            }

            assert len(pending_results) == 321
            assert len(hbeat.measured_fp_set) == 0
            log.debug("Before wait_for_results.")
            scanner.wait_for_results(executor, hbeat, rd, pending_results)
            log.debug("After wait_for_results")
            for pending_result in pending_results:
                assert pending_result.done() is True
            assert len(hbeat.measured_fp_set) == 321
            scanner.force_get_results(pending_results)
            log.debug("After force_get_results.")
            assert concurrent.futures.ALL_COMPLETED
