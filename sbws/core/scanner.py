""" Measure the relays. """
import concurrent.futures
import logging
import os
import queue
import random
import signal
import sys
import threading
import time
import traceback
import uuid
from argparse import ArgumentDefaultsHelpFormatter

import sbws.util.requests as requests_utils
import sbws.util.stem as stem_utils
from sbws.globals import HTTP_GET_HEADERS, SOCKET_TIMEOUT, fail_hard

from .. import settings
from ..lib.circuitbuilder import GapsCircuitBuilder as CB
from ..lib.destination import (
    DestinationList,
    connect_to_destination_over_circuit,
)
from ..lib.heartbeat import Heartbeat
from ..lib.relaylist import RelayList
from ..lib.relayprioritizer import RelayPrioritizer
from ..lib.resultdump import (
    ResultDump,
    ResultError,
    ResultErrorCircuit,
    ResultErrorDestination,
    ResultErrorSecondRelay,
    ResultErrorStream,
    ResultSuccess,
)
from ..util.state import State
from ..util.timestamp import now_isodt_str

rng = random.SystemRandom()
log = logging.getLogger(__name__)
# Declare the objects that manage the threads global so that sbws can exit
# gracefully at any time.
rd = None
controller = None

FILLUP_TICKET_MSG = """Something went wrong.
Please create an issue at
https://gitlab.torproject.org/tpo/network-health/sbws/-/issues with this
traceback."""


def stop_threads(signal, frame, exit_code=0):
    global rd
    log.debug("Stopping sbws.")
    # Avoid new threads to start.
    settings.set_end_event()
    # Stop ResultDump thread
    rd.thread.join()
    # Stop Tor thread
    controller.close()
    sys.exit(exit_code)


signal.signal(signal.SIGTERM, stop_threads)


def dumpstacks():
    log.critical(FILLUP_TICKET_MSG)
    thread_id2name = dict([(t.ident, t.name) for t in threading.enumerate()])
    for thread_id, stack in sys._current_frames().items():
        log.critical(
            "Thread: %s(%d)", thread_id2name.get(thread_id, ""), thread_id
        )
        log.critical("Traceback: %s", "".join(traceback.format_stack(stack)))


def sigint_handler():
    import pdb

    pdb.set_trace()


signal.signal(signal.SIGINT, sigint_handler)


def timed_recv_from_server(session, dest, byte_range):
    """Request the **byte_range** from the URL at **dest**. If successful,
    return True and the time it took to download. Otherwise return False and an
    exception."""

    start_time = time.time()
    HTTP_GET_HEADERS["Range"] = byte_range
    # - response.elapsed "measures the time taken between sending the first
    #   byte of the request and finishing parsing the headers.
    #   It is therefore unaffected by consuming the response content"
    #   If this mean that the content has arrived, elapsed could be used to
    #   know the time it took.
    try:
        # headers are merged with the session ones, not overwritten.
        session.get(dest.url, headers=HTTP_GET_HEADERS, verify=dest.verify)
    # All `requests` exceptions could be caught with
    # `requests.exceptions.RequestException`, but it seems that `requests`
    # does not catch all the ssl exceptions and urllib3 doesn't seem to have
    # a base exception class.
    except Exception as e:
        log.debug(e)
        return False, e
    end_time = time.time()
    return True, end_time - start_time


def get_random_range_string(content_length, size):
    """
    Return a random range of bytes of length **size**. **content_length** is
    the size of the file we will be requesting a range of bytes from.

    For example, for content_length of 100 and size 10, this function will
    return one of the following: '0-9', '1-10', '2-11', [...] '89-98', '90-99'
    """
    assert size <= content_length
    # start can be anywhere in the content_length as long as it is **size**
    # bytes away from the end or more. Because range is [start, end) (doesn't
    # include the end value), add 1 to the end.
    start = rng.choice(range(0, content_length - size + 1))
    # Unlike range, the byte range in an http header is [start, end] (does
    # include the end value), so we subtract one
    end = start + size - 1
    # start and end are indexes, while content_length is a length, therefore,
    # the largest index end should ever be should be less than the total length
    # of the content. For example, if content_length is 10, end could be
    # anywhere from 0 to 9.
    assert end < content_length
    return "bytes={}-{}".format(start, end)


def measure_rtt_to_server(session, conf, dest, content_length):
    """Make multiple end-to-end RTT measurements by making small HTTP requests
    over a circuit + stream that should already exist, persist, and not need
    rebuilding. If something goes wrong and not all of the RTT measurements can
    be made, return None. Otherwise return a list of the RTTs (in seconds).

    :returns tuple: results or None if the if the measurement fail.
        None or exception if the measurement fail.

    """
    rtts = []
    size = conf.getint("scanner", "min_download_size")
    for _ in range(0, conf.getint("scanner", "num_rtts")):
        log.debug("Measuring RTT to %s", dest.url)
        random_range = get_random_range_string(content_length, size)
        success, data = timed_recv_from_server(session, dest, random_range)
        if not success:
            # data is an exception
            log.debug(
                "While measuring the RTT to %s we hit an exception "
                "(does the webserver support Range requests?): %s",
                dest.url,
                data,
            )
            return None, data
        assert success
        # data is an RTT
        assert isinstance(data, float) or isinstance(data, int)
        rtts.append(data)
    return rtts, None


def measure_bandwidth_to_server(session, conf, dest, content_length):
    """
    :returns tuple: results or None if the if the measurement fail.
        None or exception if the measurement fail.

    """
    results = []
    num_downloads = conf.getint("scanner", "num_downloads")
    expected_amount = conf.getint("scanner", "initial_read_request")
    min_dl = conf.getint("scanner", "min_download_size")
    max_dl = conf.getint("scanner", "max_download_size")
    download_times = {
        "toofast": conf.getfloat("scanner", "download_toofast"),
        "min": conf.getfloat("scanner", "download_min"),
        "target": conf.getfloat("scanner", "download_target"),
        "max": conf.getfloat("scanner", "download_max"),
    }
    while len(results) < num_downloads and not settings.end_event.is_set():
        assert expected_amount >= min_dl
        assert expected_amount <= max_dl
        random_range = get_random_range_string(content_length, expected_amount)
        success, data = timed_recv_from_server(session, dest, random_range)
        if not success:
            # data is an exception
            log.debug(
                "While measuring the bandwidth to %s we hit an "
                "exception (does the webserver support Range "
                "requests?): %s",
                dest.url,
                data,
            )
            return None, data
        assert success
        # data is a download time
        assert isinstance(data, float) or isinstance(data, int)
        if _should_keep_result(
            expected_amount == max_dl, data, download_times
        ):
            results.append({"duration": data, "amount": expected_amount})
        expected_amount = _next_expected_amount(
            expected_amount, data, download_times, min_dl, max_dl
        )
    return results, None


def _pick_ideal_second_hop(relay, dest, rl, cont, is_exit):
    """
    Sbws builds two hop circuits. Given the **relay** to measure with
    destination **dest**, pick a second relay that is or is not an exit
    according to **is_exit**.
    """
    # 40041: Instead of using exits that can exit to all IPs, to ensure that
    # they can make requests to the Web servers, try with the exits that
    # allow some IPs, since there're more.
    # In the case that a concrete exit can't exit to the Web server, it is not
    # a problem since the relay will be measured in the next loop with other
    # random exit.
    candidates = (
        rl.exits_not_bad_allowing_port(dest.port) if is_exit else rl.non_exits
    )
    if not len(candidates):
        return None
    # In the case the helper is an exit, the entry could be an exit too
    # (#40041), so ensure the helper is not the same as the entry, likely to
    # happen in a test network.
    if is_exit:
        candidates = [
            c for c in candidates if c.fingerprint != relay.fingerprint
        ]
    min_relay_bw = rl.exit_min_bw() if is_exit else rl.non_exit_min_bw()
    log.debug(
        "Picking a 2nd hop to measure %s from %d choices. is_exit=%s",
        relay.nickname,
        len(candidates),
        is_exit,
    )
    for min_bw_factor in [2, 1.75, 1.5, 1.25, 1]:
        min_bw = relay.consensus_bandwidth * min_bw_factor
        # We might have a really slow/new relay. Try to measure it properly by
        # using only relays with or above our calculated min_relay_bw (see:
        # _calculate_min_bw_second_hop() in relaylist.py).
        if min_bw < min_relay_bw:
            min_bw = min_relay_bw
        new_candidates = stem_utils.only_relays_with_bandwidth(
            cont, candidates, min_bw=min_bw
        )
        if len(new_candidates) > 0:
            chosen = rng.choice(new_candidates)
            log.debug(
                "Found %d candidate 2nd hops with at least %sx the bandwidth "
                "of %s. Returning %s (bw=%s).",
                len(new_candidates),
                min_bw_factor,
                relay.nickname,
                chosen.nickname,
                chosen.consensus_bandwidth,
            )
            return chosen
    candidates = sorted(
        candidates, key=lambda r: r.consensus_bandwidth, reverse=True
    )
    chosen = candidates[0]
    log.debug(
        "Didn't find any 2nd hops at least as fast as %s (bw=%s). It's "
        "probably really fast. Returning %s (bw=%s), the fastest "
        "candidate we have.",
        relay.nickname,
        relay.consensus_bandwidth,
        chosen.nickname,
        chosen.consensus_bandwidth,
    )
    return chosen


def error_no_helper(relay, dest, our_nick=""):
    reason = "Unable to select a second relay"
    log.debug(
        reason + " to help measure %s (%s)", relay.fingerprint, relay.nickname
    )
    return [
        ResultErrorSecondRelay(relay, [], dest.url, our_nick, msg=reason),
    ]


def create_path_relay(relay, dest, rl, cb, relay_as_entry=True):
    # the helper `is_exit` arg (should be better called `helper_as_exit`),
    # is True when the relay is the entry (helper has to be exit)
    # and False when the relay is not the entry, ie. is the exit (helper does
    # not have to be an exit)
    helper = _pick_ideal_second_hop(
        relay, dest, rl, cb.controller, is_exit=relay_as_entry
    )
    if not helper:
        return error_no_helper(relay, dest)
    if relay_as_entry:
        circ_fps = [relay.fingerprint, helper.fingerprint]
        nicknames = [relay.nickname, helper.nickname]
        exit_policy = helper.exit_policy
    else:
        circ_fps = [helper.fingerprint, relay.fingerprint]
        nicknames = [helper.nickname, relay.nickname]
        exit_policy = relay.exit_policy
    return circ_fps, nicknames, exit_policy


def error_no_circuit(circ_fps, nicknames, reason, relay, dest, our_nick):
    log.debug(
        "Could not build circuit with path %s (%s): %s ",
        circ_fps,
        nicknames,
        reason,
    )
    return [
        ResultErrorCircuit(relay, circ_fps, dest.url, our_nick, msg=reason),
    ]


def measure_relay(args, conf, destinations, cb, rl, relay):
    """
    Select a Web server, a relay to build the circuit,
    build the circuit and measure the bandwidth of the given relay.

    :return Result: a measurement Result object

    """
    log.debug("Measuring %s %s", relay.nickname, relay.fingerprint)
    our_nick = conf["scanner"]["nickname"]
    s = requests_utils.make_session(
        cb.controller, conf.getfloat("general", "http_timeout")
    )
    # Probably because the scanner is stopping.
    if s is None:
        if settings.end_event.is_set():
            return None
        else:
            # In future refactor this should be returned from the make_session
            reason = "Unable to get proxies."
            log.debug(
                reason + " to measure %s %s", relay.nickname, relay.fingerprint
            )
            return [
                ResultError(relay, [], "", our_nick, msg=reason),
            ]
    # Pick a destination
    dest = destinations.next()
    # When there're no any functional destinations.
    if not dest:
        # NOTE: When there're still functional destinations but only one of
        # them fail, the error will be included in `ResultErrorStream`.
        # Since this is being executed in a thread, the scanner can not
        # be stop here, but the `end_event` signal can be set so that the
        # main thread stop the scanner.
        # It might be useful to store the fact that the destinations fail,
        # so store here the error, and set the signal once the error is stored
        # (in `resultump`).
        log.critical(
            "There are not any functional destinations.\n"
            "It is recommended to set several destinations so that "
            "the scanner can continue if one fails."
        )
        reason = "No functional destinations"
        # Resultdump will set end_event after storing the error
        return [
            ResultErrorDestination(relay, [], "", our_nick, msg=reason),
        ]

    # Pick a relay to help us measure the given relay. If the given relay is an
    # exit, then pick a non-exit. Otherwise pick an exit.
    # Instead of ensuring that the relay can exit to all IPs, try first with
    # the relay as an exit, if it can exit to some IPs.
    if relay.is_exit_not_bad_allowing_port(dest.port):
        r = create_path_relay(relay, dest, rl, cb, relay_as_entry=False)
    else:
        r = create_path_relay(relay, dest, rl, cb)
    # When `error_no_helper` is triggered because a helper is not found, what
    # can happen in test networks with very few relays, it returns a list with
    # the error.
    if len(r) == 1:
        return r
    circ_fps, nicknames, exit_policy = r

    # Build the circuit
    circ_id, reason = cb.build_circuit(circ_fps)

    # If the circuit failed to get created, bad luck, it will be created again
    # with other helper.
    # Here we won't have the case that an exit tried to build the circuit as
    # entry and failed (#40029), cause not checking that it can exit all IPs.
    if not circ_id:
        return error_no_circuit(
            circ_fps, nicknames, reason, relay, dest, our_nick
        )
    log.debug(
        "Built circuit with path %s (%s) to measure %s (%s)",
        circ_fps,
        nicknames,
        relay.fingerprint,
        relay.nickname,
    )
    # Make a connection to the destination
    is_usable, usable_data = connect_to_destination_over_circuit(
        dest, circ_id, s, cb.controller, dest._max_dl
    )

    # In the case that the relay was used as an exit, but could not exit
    # to the Web server, try again using it as entry, to avoid that it would
    # always fail when there's only one Web server.
    if not is_usable and relay.is_exit_not_bad_allowing_port(dest.port):
        log.debug(
            "Exit %s (%s) that can't exit all ips, with exit policy %s, failed"
            " to connect to %s via circuit %s (%s). Reason: %s. Trying again "
            "with it as entry.",
            relay.fingerprint,
            relay.nickname,
            exit_policy,
            dest.url,
            circ_fps,
            nicknames,
            usable_data,
        )
        r = create_path_relay(relay, dest, rl, cb)
        if len(r) == 1:
            return r
        circ_fps, nicknames, exit_policy = r
        circ_id, reason = cb.build_circuit(circ_fps)
        if not circ_id:
            log.info(
                "Exit %s (%s) that can't exit all ips, failed to create "
                " circuit as entry: %s (%s).",
                relay.fingerprint,
                relay.nickname,
                circ_fps,
                nicknames,
            )
            return error_no_circuit(
                circ_fps, nicknames, reason, relay, dest, our_nick
            )

        log.debug(
            "Built circuit with path %s (%s) to measure %s (%s)",
            circ_fps,
            nicknames,
            relay.fingerprint,
            relay.nickname,
        )
        is_usable, usable_data = connect_to_destination_over_circuit(
            dest, circ_id, s, cb.controller, dest._max_dl
        )
    if not is_usable:
        log.debug(
            "Failed to connect to %s to measure %s (%s) via circuit "
            "%s (%s). Exit policy: %s. Reason: %s.",
            dest.url,
            relay.fingerprint,
            relay.nickname,
            circ_fps,
            nicknames,
            exit_policy,
            usable_data,
        )
        cb.close_circuit(circ_id)
        return [
            ResultErrorStream(
                relay, circ_fps, dest.url, our_nick, msg=usable_data
            ),
        ]
    assert is_usable
    assert "content_length" in usable_data
    # FIRST: measure RTT
    rtts, reason = measure_rtt_to_server(
        s, conf, dest, usable_data["content_length"]
    )
    if rtts is None:
        log.debug(
            "Unable to measure RTT for %s (%s) to %s via circuit "
            "%s (%s): %s",
            relay.fingerprint,
            relay.nickname,
            dest.url,
            circ_fps,
            nicknames,
            reason,
        )
        cb.close_circuit(circ_id)
        return [
            ResultErrorStream(
                relay, circ_fps, dest.url, our_nick, msg=str(reason)
            ),
        ]
    # SECOND: measure bandwidth
    bw_results, reason = measure_bandwidth_to_server(
        s, conf, dest, usable_data["content_length"]
    )
    if bw_results is None:
        log.debug(
            "Failed to measure %s (%s) via circuit %s (%s) to %s. Exit"
            " policy: %s. Reason: %s.",
            relay.fingerprint,
            relay.nickname,
            circ_fps,
            nicknames,
            dest.url,
            exit_policy,
            reason,
        )
        cb.close_circuit(circ_id)
        return [
            ResultErrorStream(
                relay, circ_fps, dest.url, our_nick, msg=str(reason)
            ),
        ]
    cb.close_circuit(circ_id)
    # Finally: store result
    log.debug(
        "Success measurement for %s (%s) via circuit %s (%s) to %s",
        relay.fingerprint,
        relay.nickname,
        circ_fps,
        nicknames,
        dest.url,
    )
    return [
        ResultSuccess(rtts, bw_results, relay, circ_fps, dest.url, our_nick),
    ]


def dispatch_worker_thread(*a, **kw):
    # If at the point where the relay is actually going to be measured there
    # are not any functional destinations or the `end_event` is set, do not
    # try to start measuring the relay, since it will fail anyway.
    try:
        # a[2] is the argument `destinations`
        functional_destinations = a[2].functional_destinations
    # In case the arguments or the method change, catch the possible exceptions
    # but ignore here that there are not destinations.
    except (IndexError, TypeError):
        log.debug("Wrong argument or attribute.")
        functional_destinations = True
    if not functional_destinations or settings.end_event.is_set():
        return None
    return measure_relay(*a, **kw)


def _should_keep_result(did_request_maximum, result_time, download_times):
    # In the normal case, we didn't ask for the maximum allowed amount. So we
    # should only allow ourselves to keep results that are between the min and
    # max allowed time
    msg = "Keeping measurement time {:.2f}".format(result_time)
    if (
        not did_request_maximum
        and result_time >= download_times["min"]
        and result_time < download_times["max"]
    ):
        log.debug(msg)
        return True
    # If we did request the maximum amount, we should keep the result as long
    # as it took less than the maximum amount of time
    if did_request_maximum and result_time < download_times["max"]:
        log.debug(msg)
        return True
    # In all other cases, return false
    log.debug(
        "Not keeping result time %f.%s",
        result_time,
        ""
        if not did_request_maximum
        else " We requested the maximum " "amount allowed.",
    )
    return False


def _next_expected_amount(
    expected_amount, result_time, download_times, min_dl, max_dl
):
    if result_time < download_times["toofast"]:
        # Way too fast, greatly increase the amount we ask for
        expected_amount = int(expected_amount * 5)
    elif (
        result_time < download_times["min"]
        or result_time >= download_times["max"]
    ):
        # As long as the result is between min/max, keep the expected amount
        # the same. Otherwise, adjust so we are aiming for the target amount.
        expected_amount = int(
            expected_amount * download_times["target"] / result_time
        )
    # Make sure we don't request too much or too little
    expected_amount = max(min_dl, expected_amount)
    expected_amount = min(max_dl, expected_amount)
    return expected_amount


def measurement_writer(result_dump, measurement):
    # Since result_dump thread is calling queue.get() every second,
    # the queue should be full for only 1 second.
    # This call blocks at maximum timeout seconds.
    try:
        result_dump.queue.put(measurement, timeout=3)
    except queue.Full:
        # The result would be lost, the scanner will continue working.
        log.warning(
            "The queue with measurements is full, when adding %s.\n"
            "It is possible that the thread that get them to "
            "write them to the disk (ResultDump.enter) is stalled.",
            measurement,
        )


def log_measurement_exception(target, exception):
    print("in result putter error")
    if settings.end_event.is_set():
        return
    # The only object that can be here if there is not any uncatched
    # exception is stem.SocketClosed when stopping sbws
    # An exception here means that the worker thread finished.
    log.warning(FILLUP_TICKET_MSG)
    # To print the traceback that happened in the thread, not here in
    # the main process.
    log.warning(
        "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        )
    )
    log.debug(
        "".join(
            target.fingerprint,
            target.nickname,
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            ),
        )
    )


def main_loop(
    args,
    conf,
    controller,
    relay_list,
    circuit_builder,
    result_dump,
    relay_prioritizer,
    destinations,
):
    r"""Create the queue of future measurements for every relay to measure.

    It starts a loop that will be run while there is not and event signaling
    that sbws is stopping (because of SIGTERM or SIGINT).

    Then the ``ThreadPoolExecutor`` (executor) queues all the relays to
    measure in ``Future`` objects. These objects have an ``state``.

    The executor starts a new thread for every relay to measure, which runs
    ``measure_relay`` until there are ``max_pending_results`` threads.
    After that, it will reuse a thread that has finished for every relay to
    measure.

    Then ``process_completed_futures`` is call, to obtain the results in the
    completed ``future``\s.

    """
    log.info("Started the main loop to measure the relays.")
    hbeat = Heartbeat(conf.getpath("paths", "state_fname"))

    # Set the time to wait for a thread to finish as the half of an HTTP
    # request timeout.
    # Do not start a new loop if sbws is stopping.
    while not settings.end_event.is_set():
        log.debug("Starting a new measurement loop.")
        num_relays = 0
        loop_tstart = time.time()

        # Register relay fingerprints to the heartbeat module
        hbeat.register_consensus_fprs(relay_list.relays_fingerprints)
        # num_threads
        max_pending_results = conf.getint("scanner", "measurement_threads")
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_pending_results, thread_name_prefix="measurer"
        ) as executor:
            log.info("In the executor, queue all future measurements.")
            # With futures, there's no need for callback, what it was the
            # callback with multiprocessing library can be just a function
            # that gets executed when the future result is obtained.
            pending_results = {
                executor.submit(
                    dispatch_worker_thread,
                    args,
                    conf,
                    destinations,
                    circuit_builder,
                    relay_list,
                    target,
                ): target
                for target in relay_prioritizer.best_priority()
            }
            log.debug("Measurements queued.")
            # After the submitting all the targets to the executor, the pool
            # has queued all the relays and pending_results has the list of all
            # `Future`s.

            # Each target relay_recent_measurement_attempt is incremented in
            # `process_completed_futures` as well as hbeat measured
            # fingerprints.
            num_relays = len(pending_results)
            # Without a callback, it's needed to pass `result_dump` here to
            # call the function that writes the measurement when it's
            # finished.
            process_completed_futures(
                executor,
                hbeat,
                result_dump,
                pending_results,
            )
            wait_futures_completed(pending_results)

        # Print the heartbeat message
        hbeat.print_heartbeat_message()

        loop_tstop = time.time()
        loop_tdelta = (loop_tstop - loop_tstart) / 60
        # At this point, we know the relays that were queued to be
        # measured.
        log.debug(
            "Attempted to measure %s relays in %i minutes.",
            num_relays,
            loop_tdelta,
        )
        # In a testing network, exit after first loop
        if controller.get_conf("TestingTorNetwork") == "1":
            log.info("In a testing network, exiting after the first loop.")
            # Threads should be closed nicely in some refactor
            stop_threads(signal.SIGTERM, None)


def process_completed_futures(executor, hbeat, result_dump, pending_results):
    """Obtain the relays' measurements as they finish.

    For every ``Future`` measurements that gets completed, obtain the
    ``result`` and call ``measurement_writer``, which put the ``Result`` in
    ``ResultDump`` queue and complete immediately.

    ``ResultDump`` thread (started before and out of this function) will get
    the ``Result`` from the queue and write it to disk, so this doesn't block
    the measurement threads.

    If there was an exception not caught by ``measure_relay``, it will call
    instead ``log_measurement_exception``, which logs the error and complete
    immediately.

    """
    num_relays_to_measure = num_pending_results = len(pending_results)
    with executor:
        for future_measurement in concurrent.futures.as_completed(
            pending_results
        ):
            target = pending_results[future_measurement]
            # 40023, disable to decrease state.dat json lines
            # relay_list.increment_recent_measurement_attempt()
            target.increment_relay_recent_measurement_attempt()

            # Register this measurement to the heartbeat module
            hbeat.register_measured_fpr(target.fingerprint)
            log.debug(
                "Future measurement for target %s (%s) is done: %s",
                target.fingerprint,
                target.nickname,
                future_measurement.done(),
            )
            try:
                measurement = future_measurement.result()
            except Exception as e:
                log_measurement_exception(target, e)
                import psutil

                log.warning(psutil.Process(os.getpid()).memory_full_info())
                virtualMemoryInfo = psutil.virtual_memory()
                availableMemory = virtualMemoryInfo.available
                log.warning(
                    "Memory available %s MB.", availableMemory / 1024**2
                )
                dumpstacks()
            else:
                log.info("Measurement ready: %s" % (measurement))
                measurement_writer(result_dump, measurement)
            # `pending_results` has all the initial queued `Future`s,
            # they don't decrease as they get completed, but we know 1 has be
            # completed in each loop,
            num_pending_results -= 1
            log.info(
                "Pending measurements: %s out of %s: ",
                num_pending_results,
                num_relays_to_measure,
            )


def wait_futures_completed(pending_results):
    """Wait for last futures to finish, before starting new loop."""
    log.info("Wait for any remaining measurements.")
    done, not_done = concurrent.futures.wait(
        pending_results,
        timeout=SOCKET_TIMEOUT + 10,  # HTTP timeout is 10
        return_when=concurrent.futures.ALL_COMPLETED,
    )
    log.info("Completed futures: %s", len(done))
    # log.debug([f.__dict__ for f in done])
    cancelled = [f for f in done if f.cancelled()]
    if cancelled:
        log.warning("Cancelled futures: %s", len(cancelled))
        for f, t in cancelled:
            log.debug(t.fingerprint)
            dumpstacks()
    if not_done:
        log.warning("Not completed futures: %s", len(not_done))
        for f, t in not_done:
            log.debug(t.fingerprint)
            dumpstacks()


def run_speedtest(args, conf):
    """Initializes all the data and threads needed to measure the relays.

    It launches or connect to Tor in a thread.
    It initializes the list of relays seen in the Tor network.
    It starts a thread to read the previous measurements and wait for new
    measurements to write them to the disk.
    It initializes a class that will be used to order the relays depending
    on their measurements age.
    It initializes the list of destinations that will be used for the
    measurements.
    It initializes the thread pool that will launch the measurement threads.
    The pool starts 3 other threads that are not the measurement (worker)
    threads.
    Finally, it calls the function that will manage the measurement threads.

    """
    global rd, controller

    controller = stem_utils.launch_or_connect_to_tor(conf)

    # When there will be a refactor where conf is global, this can be removed
    # from here.
    state = State(conf.getpath("paths", "state_fname"))
    # XXX: tech-debt: create new function to obtain the controller and to
    # write the state, so that a unit test to check the state tor version can
    # be created
    # Store tor version whenever the scanner starts.
    state["tor_version"] = str(controller.get_version())
    # Call only once to initialize http_headers
    settings.init_http_headers(
        conf.get("scanner", "nickname"), state["uuid"], state["tor_version"]
    )
    # To do not have to pass args and conf to RelayList, pass an extra
    # argument with the data_period
    measurements_period = conf.getint("general", "data_period")
    rl = RelayList(args, conf, controller, measurements_period, state)
    cb = CB(args, conf, controller, rl)
    rd = ResultDump(args, conf)
    rp = RelayPrioritizer(args, conf, rl, rd)
    destinations, error_msg = DestinationList.from_config(
        conf, cb, rl, controller
    )
    if not destinations:
        fail_hard(error_msg)
    try:
        main_loop(args, conf, controller, rl, cb, rd, rp, destinations)
    except KeyboardInterrupt:
        log.info("Interrupted by the user.")
        dumpstacks()
    except Exception as e:
        log.exception(e)
        dumpstacks()


def gen_parser(sub):
    d = (
        "The scanner side of sbws. This should be run on a well-connected "
        "machine on the Internet with a healthy amount of spare bandwidth. "
        "This continuously builds circuits, measures relays, and dumps "
        "results into a datadir, commonly found in ~/.sbws"
    )
    sub.add_parser(
        "scanner", formatter_class=ArgumentDefaultsHelpFormatter, description=d
    )


def main(args, conf):
    if conf.getint("scanner", "measurement_threads") < 1:
        fail_hard("Number of measurement threads must be larger than 1")

    min_dl = conf.getint("scanner", "min_download_size")
    max_dl = conf.getint("scanner", "max_download_size")
    if max_dl < min_dl:
        fail_hard(
            "Max download size %d cannot be smaller than min %d",
            max_dl,
            min_dl,
        )

    os.makedirs(conf.getpath("paths", "datadir"), exist_ok=True)

    state = State(conf.getpath("paths", "state_fname"))
    state["scanner_started"] = now_isodt_str()
    # Generate an unique identifier for each scanner
    if "uuid" not in state:
        state["uuid"] = str(uuid.uuid4())

    run_speedtest(args, conf)
