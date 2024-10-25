import copy
import logging
import random
from datetime import datetime, timedelta
from threading import Lock

from stem import ControllerError, DescriptorUnavailable, Flag

from ..globals import (
    MAX_RECENT_CONSENSUS_COUNT,
    MAX_RECENT_PRIORITY_LIST_COUNT,
    MAX_RECENT_PRIORITY_RELAY_COUNT,
    MEASUREMENTS_PERIOD,
)
from ..util import timestamps

log = logging.getLogger(__name__)


def valid_after_from_network_statuses(network_statuses):
    """Obtain the consensus Valid-After datetime from the ``document``
    attribute of a ``stem.descriptor.RouterStatusEntryV3``.

    :param list network_statuses:

    returns datetime:
    """
    for ns in network_statuses:
        document = getattr(ns, "document", None)
        if document:
            valid_after = getattr(document, "valid_after", None)
            if valid_after:
                return valid_after
    return datetime.utcnow().replace(microsecond=0)


class Relay:
    def __init__(self, fp, cont, ns=None, desc=None, timestamp=None):
        """
        Given a relay fingerprint, fetch all the information about a relay that
        sbws currently needs and store it in this class. Acts as an abstraction
        to hide the confusion that is Tor consensus/descriptor stuff.

        :param str fp: fingerprint of the relay.
        :param cont: active and valid stem Tor controller connection

        :param datatime timestamp: the timestamp of a consensus
            (RouterStatusEntryV3) from which this relay has been obtained.
        """
        if ns is not None:
            self._ns = ns
        else:
            try:
                self._ns = cont.get_network_status(fp, default=None)
            except (DescriptorUnavailable, ControllerError) as e:
                log.exception("Exception trying to get ns %s", e)
                self._ns = None
        if desc is not None:
            self._desc = desc
        else:
            try:
                self._desc = cont.get_server_descriptor(fp, default=None)
            except (DescriptorUnavailable, ControllerError) as e:
                log.exception("Exception trying to get desc %s", e)
        self.relay_in_recent_consensus = timestamps.DateTimeSeq(
            [], MAX_RECENT_CONSENSUS_COUNT
        )
        # Use the same timestamp as the consensus, so that it can be tested
        # that the relay was in a consensus using this timestamp.
        # Note that this doesn't change the number of consensus the relay was
        # in.
        self.update_relay_in_recent_consensus(timestamp)
        # The number of times that a relay is "prioritized" to be measured.
        # It is incremented in ``RelayPrioritizer.best_priority``
        self.relay_recent_priority_list = timestamps.DateTimeSeq(
            [], MAX_RECENT_PRIORITY_LIST_COUNT
        )
        # The number of times that a relay has been queued to be measured.
        # It is incremented in ``scanner.main_loop``
        self.relay_recent_measurement_attempt = timestamps.DateTimeSeq(
            [], MAX_RECENT_PRIORITY_LIST_COUNT
        )
        self.xoff_recv = timestamps.DateTimeSeq([], MAX_RECENT_CONSENSUS_COUNT)
        self.xoff_sent = timestamps.DateTimeSeq([], MAX_RECENT_CONSENSUS_COUNT)

    def _from_desc(self, attr):
        if not self._desc:
            return None
        return getattr(self._desc, attr, None)

    def _from_ns(self, attr):
        if not self._ns:
            return None
        return getattr(self._ns, attr, None)

    @property
    def nickname(self):
        return self._from_ns("nickname")

    @property
    def fingerprint(self):
        return self._from_ns("fingerprint")

    @property
    def flags(self):
        return self._from_ns("flags")

    @property
    def exit_policy(self):
        return self._from_desc("exit_policy")

    @property
    def average_bandwidth(self):
        return self._from_desc("average_bandwidth")

    @property
    def burst_bandwidth(self):
        return self._from_desc("burst_bandwidth")

    @property
    def observed_bandwidth(self):
        return self._from_desc("observed_bandwidth")

    @property
    def has_2_in_flowctrl(self):
        """
        Return True if the `FlowCtrl` field in the relay's protover consensus
        line include a value of 2 and False otherwise.

        """
        # NOTE: stem doesn't seem to obtain `pr`` nor create `protocols``
        # protocols = self._from_ns("protocols")
        protocols = self._from_desc("protocols")
        if protocols:
            if 2 in protocols.get("FlowCtrl", []):
                # log.debug("Exit %s has 2 in `FlowCtrl`.", self.nickname)
                return True
        # log.debug("Exit %s does not have 2 in `FlowCtrl`.", self.nickname)
        return False

    @property
    def consensus_bandwidth(self):
        """Return the consensus bandwidth in Bytes.

        Consensus bandwidth is the only bandwidth value that is in kilobytes.
        """
        if self._from_ns("bandwidth") is not None:
            return self._from_ns("bandwidth") * 1000

    @property
    def consensus_bandwidth_is_unmeasured(self):
        # measured appears only votes, unmeasured appears in consensus
        # therefore is_unmeasured is needed to know whether the bandwidth
        # value in consensus is coming from bwauth measurements or not.
        return self._from_ns("is_unmeasured")

    @property
    def address(self):
        return self._from_ns("address")

    @property
    def master_key_ed25519(self):
        """Obtain ed25519 master key of the relay in server descriptors.

        :returns: str, the ed25519 master key base 64 encoded without
                  trailing '='s.

        """
        # Even if this key is called master-key-ed25519 in dir-spec.txt,
        # it seems that stem parses it as ed25519_master_key
        key = self._from_desc("ed25519_master_key")
        if key is None:
            return None
        return key.rstrip("=")

    @property
    def consensus_valid_after(self):
        """Obtain the consensus Valid-After from the document of this relay
        network status.
        """
        network_status_document = self._from_ns("document")
        if network_status_document:
            return getattr(network_status_document, "valid_after", None)
        return None

    @property
    def last_consensus_timestamp(self):
        return self.relay_in_recent_consensus.last()

    def update_relay_in_recent_consensus(self, timestamp=None):
        self.relay_in_recent_consensus.update(timestamp)

    @property
    def relay_in_recent_consensus_count(self):
        """Number of times the relay was in a consensus."""
        return len(self.relay_in_recent_consensus)

    def update_xoff_sent(self, timestamp):
        if timestamp:
            self.xoff_sent.update(timestamp)

    @property
    def xoff_sent_count(self):
        return len(self.xoff_sent)

    def update_xoff_recv(self, timestamp):
        if timestamp:
            self.xoff_recv.update(timestamp)

    @property
    def xoff_recv_count(self):
        return len(self.xoff_sent)

    def can_exit_to_port(self, port, strict=False):
        """
        Returns True if the relay has an exit policy and the policy accepts
        exiting to the given port or False otherwise.

        If ``strict`` is true, it only returns the exits that can exit to all
        IPs and that port.

        The exits that are IPv6 only or IPv4 but rejecting some public networks
        will return false.
        On July 2020, there were 67 out of 1095 exits like this.

        If ``strict`` is false, it returns any exit that can exit to some
        public IPs and that port.

        Note that the EXIT flag exists when the relay can exit to 443 **and**
        80. Currently all Web servers are using 443, so it would not be needed
        to check the EXIT flag too, using this function.

        """
        # if dind't get the descriptor, there isn't exit policy
        # When the attribute is gotten in getattr(self._desc, "exit_policy"),
        # is possible that stem's _input_rules is None and raises an exception
        # (#29899):
        #   File "/usr/lib/python3/dist-packages/sbws/lib/relaylist.py", line 117, in can_exit_to_port  # noqa
        #     if not self.exit_policy:
        #   File "/usr/lib/python3/dist-packages/stem/exit_policy.py", line 512, in __len__  # noqa
        #     return len(self._get_rules())
        #   File "/usr/lib/python3/dist-packages/stem/exit_policy.py", line 464, in _get_rules  # noqa
        #     for rule in decompressed_rules:
        # TypeError: 'NoneType' object is not iterable
        # Therefore, catch the exception here.
        try:
            if self.exit_policy:
                # Using `strip_private` to ignore reject rules to private
                # networks.
                # When ``strict`` is true, We could increase the chances that
                # the exit can exit via IPv6 too (``exit_policy_v6``). However,
                # in theory that is only known using microdescriptors.
                return self.exit_policy.strip_private().can_exit_to(
                    port=port, strict=strict
                )
        except TypeError:
            return False
        return False

    def is_exit_not_bad_allowing_port(self, port, strict=False):
        return (
            Flag.BADEXIT not in self.flags
            and Flag.EXIT in self.flags
            and self.can_exit_to_port(port, strict)
        )

    def increment_relay_recent_measurement_attempt(self):
        """
        Increment The number of times that a relay has been queued
        to be measured.

        It is call from :func:`~sbws.core.scaner.main_loop`.
        """
        self.relay_recent_measurement_attempt.update()

    @property
    def relay_recent_measurement_attempt_count(self):
        return len(self.relay_recent_measurement_attempt)

    def increment_relay_recent_priority_list(self):
        """
        The number of times that a relay is "prioritized" to be measured.

        It is call from
        :meth:`~sbws.lib.relayprioritizer.RelayPrioritizer.best_priority`.
        """
        # If it was not in the previous measurements version, start counting
        self.relay_recent_priority_list.update()

    @property
    def relay_recent_priority_list_count(self):
        return len(self.relay_recent_priority_list)

    # XXX: tech-debt: replace `_desc` attr by a a `dequee` of the last
    # descriptors seen for this relay and the timestamp.
    def update_server_descriptor(self, server_descriptor):
        """Update this relay server descriptor (from the consensus."""
        self._desc = server_descriptor

    # XXX: tech-debt: replace `_ns` attr by a a `dequee` of the last
    # router statuses seen for this relay and the timestampt.
    def update_router_status(self, router_status):
        """Update this relay router status (from the consensus)."""
        self._ns = router_status


class RelayList:
    """Keeps a list of all relays in the current Tor network and updates it
    transparently in the background. Provides useful interfaces for getting
    only relays of a certain type.
    """

    def __init__(
        self,
        args,
        conf,
        controller,
        measurements_period=MEASUREMENTS_PERIOD,
        state=None,
    ):
        self._controller = controller
        self.rng = random.SystemRandom()
        self._refresh_lock = Lock()
        # To track all the consensus seen.
        self._recent_consensus = timestamps.DateTimeSeq(
            [], MAX_RECENT_CONSENSUS_COUNT, state, "recent_consensus"
        )
        # Initialize so that there's no error trying to access to it.
        # In future refactor, change to a dictionary, where the keys are
        # the relays' fingerprint.
        self._relays = []
        # The period of time for which the measurements are keep.
        self._measurements_period = measurements_period
        self._recent_measurement_attempt = timestamps.DateTimeSeq(
            [],
            MAX_RECENT_PRIORITY_RELAY_COUNT,
            state,
            "recent_measurement_attempt",
        )
        # Start with 0 for the min bw for our second hops
        self._exit_min_bw = 0
        self._non_exit_min_bw = 0
        self._refresh()

    def _need_refresh(self):
        # New consensuses happen every hour.
        return datetime.utcnow() >= self.last_consensus_timestamp + timedelta(
            seconds=60 * 60
        )

    @property
    def last_consensus_timestamp(self):
        """Returns the datetime when the last consensus was obtained."""
        return self._recent_consensus.last()

    @property
    def relays(self):
        # See if we can get the list of relays without having to do a refresh,
        # which is expensive and blocks other threads
        if self._need_refresh():
            log.debug(
                "We need to refresh our list of relays. "
                "Going to wait for lock."
            )
            # Whelp we couldn't just get the list of relays because the list is
            # stale. Wait for the lock so we can refresh it.
            with self._refresh_lock:
                log.debug(
                    "We got the lock. Now to see if we still "
                    "need to refresh."
                )
                # Now we have the lock ... but wait! Maybe someone else already
                # did the refreshing. So check if it still needs refreshing. If
                # not, we can do nothing.
                if self._need_refresh():
                    log.debug("Yup we need to refresh our relays. Doing so.")
                    self._refresh()
                else:
                    log.debug(
                        "No we don't need to refresh our relays. "
                        "It was done by someone else."
                    )
            log.debug("Giving back the lock for refreshing relays.")
        return self._relays

    @property
    def fast(self):
        return self._relays_with_flag(Flag.FAST)

    @property
    def exits(self):
        return self._relays_with_flag(Flag.EXIT)

    @property
    def bad_exits(self):
        return self._relays_with_flag(Flag.BADEXIT)

    @property
    def non_exits(self):
        return self._relays_without_flag(Flag.EXIT)

    @property
    def guards(self):
        return self._relays_with_flag(Flag.GUARD)

    @property
    def authorities(self):
        return self._relays_with_flag(Flag.AUTHORITY)

    @property
    def relays_fingerprints(self):
        # Using relays instead of _relays, so that the list get updated if
        # needed, since this method is used to know which fingerprints are in
        # the consensus.
        return [r.fingerprint for r in self.relays]

    def random_relay(self):
        return self.rng.choice(self.relays)

    def _relays_with_flag(self, flag):
        return [r for r in self.relays if flag in r.flags]

    def _relays_without_flag(self, flag):
        return [r for r in self.relays if flag not in r.flags]

    def _init_relays(self):
        """Returns a new list of relays that are in the current consensus.
        And update the consensus timestamp list with the current one.

        """
        c = self._controller
        # This will get router statuses from this Tor cache, might not be
        # updated with the network.
        # Change to stem.descriptor.remote in future refactor.
        network_statuses = c.get_network_statuses()
        new_relays_dict = dict([(r.fingerprint, r) for r in network_statuses])
        log.debug(
            "Number of relays in the current consensus: %d.",
            len(new_relays_dict),
        )

        # Find the timestamp of the last consensus.
        timestamp = valid_after_from_network_statuses(network_statuses)
        self._recent_consensus.update(timestamp)

        new_relays = []

        # Only or debugging, count the relays that are not in the current
        # consensus and have not been seen in the last consensuses either.
        num_old_relays = 0

        relays = copy.deepcopy(self._relays)
        for r in relays:
            if r.fingerprint in new_relays_dict.keys():
                # If a relay in the previous consensus and is in the current
                # one, update its timestamp, router status and descriptor.
                fp = r.fingerprint
                # new_relays_dict[fp] is the router status.
                r.update_router_status(new_relays_dict[fp])
                r.update_relay_in_recent_consensus(timestamp)
                try:
                    descriptor = c.get_server_descriptor(fp, default=None)
                except (DescriptorUnavailable, ControllerError) as e:
                    log.exception("Exception trying to get desc %s", e)
                r.update_server_descriptor(descriptor)
                # Add it to the new list of relays.
                new_relays.append(r)
                # And remove it from the new consensus dict, as it has
                # already added to the new list.
                new_relays_dict.pop(fp)

            # In #30727, the relay that is not in the current consensus but is
            # not "old", was added to the new list of relays too.
            # In #40037 we think it should not be measured, as it might cause
            # many circuit errors. It's already added to the generator.
            # Otherwise, don't add it to the new list of relays.
            # For debugging, count the old relays that will be discarded.
            else:
                num_old_relays += 1

        # Finally, add the relays that were not in the previous consensus
        for fp, ns in new_relays_dict.items():
            r = Relay(ns.fingerprint, c, ns=ns, timestamp=timestamp)
            new_relays.append(r)

        days = self._measurements_period / (60 * 60 * 24)
        log.debug(
            "Previous number of relays being measured %d", len(self._relays)
        )
        log.debug(
            "Number of relays not in the in the consensus in the last "
            "%d days: %d.",
            days,
            num_old_relays,
        )
        log.debug(
            "Number of relays to measure with the current consensus: " "%d",
            len(new_relays),
        )
        return new_relays

    def _refresh(self):
        # Set a new list of relays.
        self._relays = self._init_relays()

        log.info(
            "Number of consensuses obtained in the last %s days: %s.",
            int(self._measurements_period / 24 / 60 / 60),
            self.recent_consensus_count,
        )

        # Calculate minimum bandwidth value for 2nd hop after we refreshed
        # our available relays.
        self._calculate_min_bw_second_hop()
        self.set_consensus_params()

    @property
    def recent_consensus_count(self):
        """Number of times a new consensus was obtained."""
        return len(self._recent_consensus)

    def exits_with_2_in_flowctrl(self, port):
        """
        Return the exits that include a value of 2 in the `FlowCtrl` field
        in their protover consensus line.

        """
        exits_flowctrl2 = [
            r
            for r in self.exits_not_bad_allowing_port(port)
            if r.has_2_in_flowctrl
        ]
        # In chutney, just take relays with exit flag
        if (
            not exits_flowctrl2
            and self._controller.get_conf("TestingTorNetwork") == "1"
        ):
            exits_flowctrl2 = list(
                filter(lambda r: r.has_2_in_flowctrl, self.exits)
            )
        return exits_flowctrl2

    def exits_without_2_in_flowctrl(self, port):
        """
        Return the exits that do not include a value of 2 in the `FlowCtrl`
        field in their protover consensus line or the field is missing.

        """
        return [
            r
            for r in self.exits_not_bad_allowing_port(port)
            if not r.has_2_in_flowctrl
        ]

    def set_consensus_params(self):
        """Obtain current consensus params fields and store them as an attr.

        It is not possible to obtain them from `get_network_statuses` via
        control port, only via a cached file.

        """
        if self._controller.get_conf("TestingTorNetwork") == "1":
            log.debug("In a testing network.")
            self.consensus_params_dict = {"cc_alg": 2, "bwscanner_cc": 2}
            return
        log.debug("Not in a testing network.")
        consensus = self._controller.get_info(
            "dir/status-vote/current/consensus"
        )
        from unittest import mock

        if isinstance(consensus, mock.Mock):
            log.debug("Mocked consensus.")
            self.consensus_params_dict = {}
            return
        # Create a dictionary from all the consensus lines.
        consensus_dict = dict(
            [
                (line.split(" ")[0], line.split()[1:])
                for line in consensus.split("\n")
            ]
        )
        # Create a dictionary from the consensus `params` line.
        self.consensus_params_dict = dict(
            [
                (p.split("=")[0], int(p.split("=")[1]))
                for p in consensus_dict.get("params", [])
            ]
        )
        log.debug("Consensus params: %s", self.consensus_params_dict.items())

    @property
    def is_consensus_cc_alg_2(self):
        """
        Return True if the consensus document has a value of 2 in the `cc_alg`
        field.

        From proposals/324-rtt-congestion-control.txt spec::

            6.5.1. Parameters common to all algorithms
            [...]
            cc_alg:
            - Description:
                Specifies which congestion control algorithm clients should
                use, as an integer.
            - Range: [0,3]  (0=fixed, 1=Westwood, 2=Vegas, 3=NOLA)
            - Default: 2

        """
        if (
            self.consensus_params_dict
            and self.consensus_params_dict.get("cc_alg", 0) == 2
        ):
            log.info("The consensus implements congestion control.")
            return True
        log.info("The consensus does not implement congestion control.")
        return False

    @property
    def is_consensus_bwscanner_cc_gte_1(self):
        """
        Return True if the consensus document has a value of 1 or greater in
        the `bwscanner_cc` field."""
        if (
            self.consensus_params_dict
            and self.consensus_params_dict.get("bwscanner_cc", 0) >= 1
        ):
            log.info(
                "The consensus says to use exits that support congestion"
                " control."
            )
            return True
        log.info(
            "The consensus says to use exits that do not support congestion"
            " control."
        )
        return False

    @property
    def is_consensus_bwscanner_cc_2(self):
        """Return True if the consensus document has a value of 2 in
        the `bwscanner_cc` field."""
        if (
            self.consensus_params_dict
            and self.consensus_params_dict.get("bwscanner_cc", 0) == 2
        ):
            log.info(
                "The consensus says to upload data instead of download it."
            )
            return True
        log.info("The consensus says to download data.")
        return False

    def exits_not_bad_allowing_port(self, port, strict=False):
        return [
            r
            for r in self.exits
            if r.is_exit_not_bad_allowing_port(port, strict)
        ]

    def increment_recent_measurement_attempt(self):
        """
        Increment the number of times that any relay has been queued to be
        measured.

        It is call from :func:`~sbws.core.scaner.main_loop`.

        It is read and stored in a ``state`` file.
        """
        # NOTE: blocking, writes to file!
        self._recent_measurement_attempt.update()

    @property
    def recent_measurement_attempt_count(self):
        return len(self._recent_measurement_attempt)

    def _calculate_min_bw_second_hop(self):
        """
        Calculates the minimum bandwidth for both exit and non-exit relays
        chosen as a second hop by picking the lowest bandwidth value available
        from the top 75% of the respective category.
        """
        # Sort our sets of candidates according to bw, lowest amount first.
        # It's okay to keep things simple for the calculation and go over all
        # exits, including badexits.
        exit_candidates = sorted(
            self.exits, key=lambda r: r.consensus_bandwidth
        )
        non_exit_candidates = sorted(
            self.non_exits, key=lambda r: r.consensus_bandwidth
        )
        # We know the bandwidth is sorted from least to most. Dividing the
        # length of the available relays by 4 gives us the position of the
        # relay with the lowest bandwidth from the top 75%. We do this both
        # for our exit and non-exit candidates.
        pos = int(len(exit_candidates) / 4)
        self._exit_min_bw = exit_candidates[pos].consensus_bandwidth
        pos = int(len(non_exit_candidates) / 4)
        # when there are not non-exits in a test network
        if pos:
            self._non_exit_min_bw = non_exit_candidates[
                pos
            ].consensus_bandwidth

    def exit_min_bw(self):
        return self._exit_min_bw

    def non_exit_min_bw(self):
        return self._non_exit_min_bw

    @property
    def sum_consensus_bw(self):
        return sum(
            list(
                map(
                    lambda r: r.consensus_bandwidth,
                    self.relays,
                )
            )
        )

    @property
    def sum_consensus_bw_exits_not_bad_allowing_port(self):
        return sum(
            list(
                map(
                    lambda r: r.consensus_bandwidth,
                    self.exits_not_bad_allowing_port(443),
                )
            )
        )

    @property
    def sum_consensus_bw_exits_flowctrl2(self):
        return sum(
            list(
                map(
                    lambda r: r.consensus_bandwidth,
                    self.exits_with_2_in_flowctrl(443),
                )
            )
        )
