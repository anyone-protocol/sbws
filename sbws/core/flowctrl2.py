import logging
from argparse import ArgumentDefaultsHelpFormatter

import sbws.util.stem as stem_utils
from sbws.lib.relaylist import RelayList
from sbws.util.state import State

log = logging.getLogger(__name__)


def gen_parser(sub):
    d = "Log the number of exits that have 2 in FlowCtrl."
    p = sub.add_parser(
        "flowctrl2",
        description=d,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    return p


def main(args, conf):
    controller = stem_utils.launch_or_connect_to_tor(conf)

    # When there will be a refactor where conf is global, this can be removed
    # from here.
    state = State(conf.getpath("paths", "state_fname"))

    measurements_period = conf.getint("general", "data_period")
    rl = RelayList(args, conf, controller, measurements_period, state)
    exits = rl.exits_not_bad_allowing_port(443)
    log.info("Number of exits: %s", len(exits))
    exits_min_bw = rl.exit_min_bw()
    log.info("Exits minimum bandwidth: %s KB.", exits_min_bw / 1000)
    exits_with_min_bw = stem_utils.only_relays_with_bandwidth(
        controller, exits, min_bw=exits_min_bw
    )
    log.info(
        "Number of exits with minimum bandwidth: %s", len(exits_with_min_bw)
    )
    exits_sorted = sorted(
        exits, key=lambda r: r.consensus_bandwidth, reverse=True
    )
    log.info(
        "Exits lowest bandwidth: %s KB.",
        exits_sorted[-1].consensus_bandwidth / 1000,
    )
    log.info(
        "Exits highest bandwidth: %s KB.",
        exits_sorted[0].consensus_bandwidth / 1000,
    )

    non_exits = rl.non_exits
    log.info("Number of non exits: %s.", len(non_exits))

    non_exits_with_helpers_double_bw = 0
    non_exits_with_helpers_same_bw = 0
    non_exits_without_helpers_same_double_bw = 0
    for relay in non_exits:
        double_min_bw = max(exits_min_bw, relay.consensus_bandwidth * 2)
        helpers = stem_utils.only_relays_with_bandwidth(
            exits_with_min_bw, min_bw=double_min_bw
        )
        if helpers:
            log.debug(
                "Number of helpers with double bandwidth for relay %s: %s.",
                relay.nickname,
                len(helpers),
            )
            non_exits_with_helpers_double_bw += 1
        else:
            min_bw = max(exits_min_bw, relay.consensus_bandwidth)
            helpers = stem_utils.only_relays_with_bandwidth(
                exits_with_min_bw, min_bw=min_bw
            )
            if helpers:
                log.debug(
                    "Number of helpers for relay %s: %s.",
                    relay.nickname,
                    len(helpers),
                )
                non_exits_with_helpers_same_bw += 1
            else:
                log.debug("No helpers for relay %s", relay.nickname)
                non_exits_without_helpers_same_double_bw += 1
    log.info(
        "Number of non exits with helpers that have double bandwidth: %s.",
        non_exits_with_helpers_double_bw,
    )
    log.info(
        "Number of non exits with helpers that have same bandwidth: %s.",
        non_exits_with_helpers_same_bw,
    )
    log.info(
        "Number of non exits without helpers that have  double or same"
        " bandwidth: %s.",
        non_exits_without_helpers_same_double_bw,
    )

    exits_flowctrl2 = rl.exits_with_2_in_flowctrl(443)
    log.info(
        "Number of exits that have 2 in FlowCtrl: %s.", len(exits_flowctrl2)
    )
    exits_flowctrl2_min_bw = stem_utils.only_relays_with_bandwidth(
        controller, exits_flowctrl2, min_bw=exits_min_bw
    )
    log.info(
        "Number of exits that have 2 in FlowCtrl and minimum bandwidth: %s",
        len(exits_flowctrl2_min_bw),
    )
    exits_flowctrl2_sorted = sorted(
        exits_flowctrl2, key=lambda r: r.consensus_bandwidth, reverse=True
    )
    log.info(
        "Exits that have 2 in FlowCtrl lowest bandwidth: %s KB.",
        exits_flowctrl2_sorted[-1].consensus_bandwidth / 1000,
    )
    log.info(
        "Exits that have 2 in FlowCtrl highest bandwidth: %s KB.",
        exits_flowctrl2_sorted[0].consensus_bandwidth / 1000,
    )

    non_exits_with_helpers_flowctrl2_double_bw = 0
    non_exits_with_helpers_flowctrl2_same_bw = 0
    non_exits_without_helpers_flowctrl2_same_double_bw = 0
    for relay in non_exits:
        double_min_bw = max(exits_min_bw, relay.consensus_bandwidth * 2)
        helpers = stem_utils.only_relays_with_bandwidth(
            controller, exits_flowctrl2_min_bw, min_bw=double_min_bw
        )
        if helpers:
            log.debug(
                "Number of helpers with double bandwidth for relay %s: %s.",
                relay.nickname,
                len(helpers),
            )
            non_exits_with_helpers_flowctrl2_double_bw += 1
        else:
            min_bw = max(exits_min_bw, relay.consensus_bandwidth)
            helpers = stem_utils.only_relays_with_bandwidth(
                controller, exits_flowctrl2_min_bw, min_bw=min_bw
            )
            if helpers:
                log.debug(
                    "Number of helpers for relay %s: %s.",
                    relay.nickname,
                    len(helpers),
                )
                non_exits_with_helpers_flowctrl2_same_bw += 1
            else:
                log.debug("No helpers for relay %s", relay.nickname)
                non_exits_without_helpers_flowctrl2_same_double_bw += 1
    log.info(
        "Number of non exits with helpers that have 2 in FlowCtrl and double"
        " bandwidth: %s.",
        non_exits_with_helpers_flowctrl2_double_bw,
    )
    log.info(
        "Number of non exits with helpers that have 2 in FlowCtrl and same"
        " bandwidth: %s.",
        non_exits_with_helpers_flowctrl2_same_bw,
    )
    log.info(
        "Number of non exits without helpers that have 2 in FlowCtrl and"
        " double or same bandwidth: %s.",
        non_exits_without_helpers_flowctrl2_same_double_bw,
    )

    sum_consensus_bw = rl.sum_consensus_bw
    log.info("Total consensus weight: %s", sum_consensus_bw / 1000)
    sum_consensus_bw_exits_not_bad_allowing_port = (
        rl.sum_consensus_bw_exits_not_bad_allowing_port
    )
    log.info(
        "Consensus weight of exits (without BAD flag, allowing 443 port): %s",
        sum_consensus_bw_exits_not_bad_allowing_port / 1000,
    )
    sum_consensus_bw_exits_flowctrl2 = rl.sum_consensus_bw_exits_flowctrl2
    log.info(
        "Cnsensus weight exits (without BAD flag, allowing 443 port)"
        " with 2 in FlowCtrl: %s",
        sum_consensus_bw_exits_flowctrl2,
    )
    fraction_flowctrl2_exits = (
        sum_consensus_bw_exits_flowctrl2
        / sum_consensus_bw_exits_not_bad_allowing_port
    )
    log.info(
        "Fraction of consensus weight of exits with 2 in FlowCtrl with respect"
        " all the exits: %.2f",
        fraction_flowctrl2_exits,
    )
