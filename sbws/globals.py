import logging
import os
import platform
from collections import OrderedDict

from requests import __version__ as requests_version
from stem import __version__ as stem_version

from sbws import __version__

log = logging.getLogger(__name__)

RESULT_VERSION = 4
WIRE_VERSION = 1
SPEC_VERSION = "1.9.0"

# This is a dictionary of torrc options we always want to set when launching
# Tor and that do not depend on any runtime configuration
# Options that are known at runtime (from configuration file) are added
# in utils/stem.py launch_tor
TORRC_STARTING_POINT = {
    # We will find out via the ControlPort and not setting something static
    # means a lower chance of conflict
    "SocksPort": "auto",
    # Easier than password authentication
    "CookieAuthentication": "0",
    # To avoid path bias warnings
    "UseEntryGuards": "0",
    # Because we need things from full server descriptors (namely for now: the
    # bandwidth line)
    "UseMicrodescriptors": "0",
    # useful logging options for clients that don't care about anonymity
    "SafeLogging": "0",
    "LogTimeGranularity": "1",
    "ProtocolWarnings": "1",
    # To be able to respond to MaxAdvertisedBandwidth as soon as possible.
    # If ``FetchDirInfoExtraEarly` is set, but not
    # `FetchDirInfoEarly`, Tor will throw this error:
    # `FetchDirInfoExtraEarly requires that you also set FetchDirInfoEarly`
    "FetchDirInfoEarly": "1",
    "FetchDirInfoExtraEarly": "1",
    # To make Tor keep fetching descriptors, even when idle.
    "FetchUselessDescriptors": "1",
    # Things needed to make circuits fail a little faster. We get the
    # circuit_timeout as a string instead of an int on purpose: stem only
    # accepts strings.
    "LearnCircuitBuildTimeout": "0",
}
# Options that need to be set at runtime.
TORRC_RUNTIME_OPTIONS = {
    # The scanner builds the circuits to download the data itself,
    # so do not let Tor to build them.
    "__DisablePredictedCircuits": "1",
    # The scanner attach the streams to the circuit itself,
    # so do not let Tor to attach them.
    "__LeaveStreamsUnattached": "1",
}
# Options that can be set at runtime and can fail with some Tor versions
# The ones that fail will be ignored..
TORRC_OPTIONS_CAN_FAIL = OrderedDict(
    {
        # Since currently scanner anonymity is not the goal, ConnectionPadding
        # is disable to do not send extra traffic
        "ConnectionPadding": "0",
    }
)

PKG_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_CONFIG_PATH = os.path.join(PKG_DIR, "config.default.ini")
DEFAULT_LOG_CONFIG_PATH = os.path.join(PKG_DIR, "config.log.default.ini")
USER_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".sbws.ini")
SUPERVISED_USER_CONFIG_PATH = "/etc/sbws/sbws.ini"
SUPERVISED_RUN_DPATH = "/run/sbws/tor"

SOCKET_TIMEOUT = 60  # seconds

# Possible `dirauth_nickname`s for BandithFiles in 2023
DIRAUTH_NICKNAMES = [
    "longclaw",
    "gabelmoo",
    "maatuska",
    "bastet",
    "moria1",
    "dannenberg",
    "dizum",
    "tor26",
    "test",
    # TODO - add DA nicknames or make configurable
    "Anon",
]
SBWS_SCALE_CONSTANT = 7500
TORFLOW_SCALING = 1
SBWS_SCALING = 2
TORFLOW_BW_MARGIN = 0.05
TORFLOW_OBS_LAST = 0
TORFLOW_OBS_MEAN = 1
TORFLOW_OBS_DECAYING = 3
TORFLOW_ROUND_DIG = 3
PROP276_ROUND_DIG = 2
# Number of seconds the measurements for a relay have to be distant from each
# other, otherwise the relay would be excluded from the relays to vote on.
# Ideally, this should be 86400 seconds (1 day).
# To have sbws vote on approximately the same number of relays as Torflow,
# leave it as None, to not exclude measurements.
DAY_SECS = None
# Minimum number of measurements for a relay to be included as a relay to vote
# on.
# Ideally, this should be 2.
# As the constant before, leave it as 1 to not exclude measurements.
NUM_MIN_RESULTS = 1
MIN_REPORT = 60
# Maximum difference between the total consensus bandwidth and the total in
# in the bandwidth lines in percentage
MAX_BW_DIFF_PERC = 50

# With the new KeyValues in #29591, the lines are greater than 510
# Tor already accept lines of any size, but leaving the limit anyway.
BW_LINE_SIZE = 1022

# RelayList, ResultDump
# For how many seconds in the past the relays and measurements data is keep/
# considered valid.
# This is currently set by default in config.default.ini as ``data_period``,
# and used in ResultDump.
# In a future refactor, constants in config.default.ini should be moved here,
# or calculated in settings, so that there's no need to pass the configuration
# to all the functions.
MEASUREMENTS_PERIOD = 5 * 24 * 60 * 60

# #40017: To make sbws behave similar to Torflow, the number of raw past
# measurements used when generating the Bandwidth File has to be 28, not 5.
# Note that this is different from the number of raw past measurements used
# when measuring, which are used for the monitoring values and storing json.
GENERATE_PERIOD = 28 * 24 * 60 * 60

# Metadata to send in every requests, so that data servers can know which
# scanners are using them.
# In Requests these keys are case insensitive.
HTTP_HEADERS = {
    # This would be ignored if changing to HTTP/2
    "Connection": "keep-alive",
    # Needs to get Tor version from the controller
    "User-Agent": "sbws/{} ({}) Python/{} Requests/{} Stem/{} Tor/".format(
        __version__,
        platform.platform(),
        platform.python_version(),
        requests_version,
        stem_version,
    ),
    # Organization defined names (:rfc:`7239`)
    # Needs to get the nickname from the user config file.
    "Tor-Bandwidth-Scanner-Nickname": "{}",
    "Tor-Bandwidth-Scanner-UUID": "{}",
    # In case of including IP address.
    # 'Forwarded': 'for={}'  # IPv6 part, if there's
}
# In the case of having ipv6 it's concatenated to forwarder.
IPV6_FORWARDED = ', for="[{}]"'

HTTP_GET_HEADERS = {
    "Range": "{}",
    "Accept-Encoding": "identity",
}
DESTINATION_VERIFY_CERTIFICATE = True
# This number might need adjusted depending on the percentage of circuits and
# HTTP requests failures.

HTTP_POST_UL_KEY = "data"
# The size of the uploaded data after the first `CIRC_BW SS=0` to stop the
# measurement
HTTP_POST_INITIAL_SIZE = int(1.5 * 1024**2)  # 1.5 MiB.
BWSCANNER_CC1 = 1
BWSCANNER_CC2 = 2

# Number of attempts to use a destination, that are stored, in order to decide
# whether the destination is functional or not.
NUM_DESTINATION_ATTEMPTS_STORED = 10
# Time to wait before trying again a destination that wasn't functional.
# Because intermittent failures with CDN destinations, start trying again
# after 5 min.
DELTA_SECONDS_RETRY_DESTINATION = 60 * 5
# No matter what, do not increase the wait time between destination reties
# past this value.
MAX_SECONDS_RETRY_DESTINATION = 60 * 60 * 3
# Number of consecutive times a destination can fail before considering it
# not functional.
MAX_NUM_DESTINATION_FAILURES = 3
# By which factor to multiply DELTA_SECONDS_RETRY_DESTINATION when the
# destination fail again.
FACTOR_INCREMENT_DESTINATION_RETRY = 2

# Constants to check health KeyValues in the bandwidth file
PERIOD_DAYS = int(MEASUREMENTS_PERIOD / (24 * 60 * 60))
MAX_RECENT_CONSENSUS_COUNT = PERIOD_DAYS * 24  # 120
# XXX: This was only defined in `config.default.ini`, it should be read from
# here.
FRACTION_RELAYS = 0.05
# A priority list currently takes more than 3h, ideally it should only take 1h.
MIN_HOURS_PRIORITY_LIST = 1
# As of 2020, there're less than 7000 relays.
MAX_RELAYS = 8000
# 120
MAX_RECENT_PRIORITY_LIST_COUNT = int(
    PERIOD_DAYS * 24 / MIN_HOURS_PRIORITY_LIST
)
MAX_RELAYS_PER_PRIORITY_LIST = int(MAX_RELAYS * FRACTION_RELAYS)  # 400
# 48000
MAX_RECENT_PRIORITY_RELAY_COUNT = (
    MAX_RECENT_PRIORITY_LIST_COUNT * MAX_RELAYS_PER_PRIORITY_LIST
)


def fail_hard(*a, **kw):
    """Log something ... and then exit as fast as possible"""
    log.critical(*a, **kw)
    exit(1)


def touch_file(fname, times=None):
    """
    If **fname** exists, update its last access and modified times to now. If
    **fname** does not exist, create it. If **times** are specified, pass them
    to os.utime for use.

    :param str fname: Name of file to update or create
    :param tuple times: 2-tuple of floats for access time and modified time
        respectively
    """
    log.debug("Touching %s", fname)
    with open(fname, "a") as fd:
        os.utime(fd.fileno(), times=times)
