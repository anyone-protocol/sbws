import logging

import pytest

from sbws.core.scanner import (
    _pick_ideal_second_hop,
    measure_relay,
    select_helper_candidates,
    use_relay_as_entry,
)
from sbws.lib.resultdump import ResultSuccess


def assert_within(value, target, radius):
    """
    Assert that **value** is within **radius** of **target**

    If target is 10 and radius is 2, value can be anywhere between 8 and 12
    inclusive
    """
    assert (
        target - radius < value
    ), "Value is too small. {} is not within " "{} of {}".format(
        value, radius, target
    )
    assert (
        target + radius > value
    ), "Value is too big. {} is not within " "{} of {}".format(
        value, radius, target
    )


@pytest.mark.skip(
    reason=(
        "Disabled because chutney is not creating a network"
        "with relay1mbyteMAB."
    )
)
def test_measure_relay_with_maxadvertisedbandwidth(
    persistent_launch_tor, sbwshome_dir, args, conf, dests, cb, rl, caplog
):
    caplog.set_level(logging.DEBUG)
    # d = get_everything_to_measure(sbwshome, cont, args, conf)
    # rl = d['rl']
    # dests = d['dests']
    # cb = d['cb']
    # 117A456C911114076BEB4E757AC48B16CC0CCC5F is relay1mbyteMAB
    relay = [r for r in rl.relays if r.nickname == "relay1mbyteMAB"][0]
    # d['relay'] = relay
    result = measure_relay(args, conf, dests, cb, rl, relay)
    assert len(result) == 1
    result = result[0]
    assert isinstance(result, ResultSuccess)
    one_mbyte = 1 * 1024 * 1024
    dls = result.downloads
    for dl in dls:
        # This relay has MaxAdvertisedBandwidth set, but should not be limited
        # to just 1 Mbyte. Assume and assert that all downloads where at least
        # more than 10% faster than 1 MBps
        assert dl["amount"] / dl["duration"] > one_mbyte * 1.1
    assert result.relay_average_bandwidth == one_mbyte


@pytest.mark.skip(reason="temporally disabled")
def test_measure_relay_with_relaybandwidthrate(
    persistent_launch_tor, args, conf, dests, cb, rl
):
    relay = [r for r in rl.relays if r.nickname == "relay1mbyteRBR"][0]
    result = measure_relay(args, conf, dests, cb, rl, relay)
    assert len(result) == 1
    result = result[0]
    assert isinstance(result, ResultSuccess)
    one_mbyte = 1 * 1024 * 1024
    allowed_error = 0.1 * one_mbyte  # allow 10% error in either direction
    dls = result.downloads
    for dl in dls:
        assert_within(dl["amount"] / dl["duration"], one_mbyte, allowed_error)


def test_second_hop_has_2_in_flowctrl(
    is_cc_tor_version, dests, rl, persistent_launch_tor
):
    if not is_cc_tor_version:
        import pytest

        pytest.skip("This test can't be run with this tor version")
        return
    rl.consensus_params_dict = {"cc_alg": 2, "bwscanner_cc": 1}
    assert rl.is_consensus_cc_alg_2
    assert rl.is_consensus_bwscanner_cc_gte_1
    dest = dests._all_dests[0]
    relay = rl._relays[0]

    relay_as_entry = use_relay_as_entry(relay, rl, dest)
    candidates = select_helper_candidates(relay, rl, dest, relay_as_entry)
    helper = _pick_ideal_second_hop(relay, rl, relay_as_entry, candidates)
    assert helper.has_2_in_flowctrl
