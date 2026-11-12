"""Physical plausibility check of relay geolocation labels.

A round trip from the scanner to a relay can not be faster than light in
fiber, about 200 km/ms one way, so a relay is at most ``100 km * RTT(ms)``
from the scanner.  When the relay's geolocation label is farther than that,
the label is physically impossible: either the GeoIP database is wrong about
the address or the address is not where it claims to be.

A relay can make its round trip time larger, never smaller.  A delay can hide
a wrong label from this check but can never make a correct label look wrong,
so every relay this check reports has a wrong label.
"""

import logging
import math
import socket
import ssl
import time

log = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0
#: Kilometers per millisecond of round trip time: light in fiber, ~2/3 c.
KM_PER_MS = 100.0
#: Kilometers per millisecond of round trip time: light in vacuum, no
#: network can be faster.
VACUUM_KM_PER_MS = 150.0
#: Allowance for labels being H3 resolution 4 cell centers (cell radius under
#: 30 km) and for the error of the scanner position.
TOLERANCE_KM = 50.0


def distance_km(a, b):
    """Great circle distance between two (latitude, longitude) points."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def label_excess_km(
    scanner, label, rtt_ms, km_per_ms=KM_PER_MS, tolerance_km=TOLERANCE_KM
):
    """Return how many km the label lies beyond the relay's reach.

    A positive value means the label is physically impossible.
    """
    return distance_km(scanner, label) - (km_per_ms * rtt_ms + tolerance_km)


def contradicts(a, b):
    """Whether two measurements of one relay can not both be true.

    :param a, b: (scanner, rtt_ms, km_per_ms, tolerance_km) tuples
    :returns: True when the two scanners are farther apart than the two
        reaches together, so no point is within reach of both.  For a correct
        setup this never happens: one of the scanner positions is wrong.
    """
    (pa, rtt_a, k_a, t_a), (pb, rtt_b, k_b, t_b) = a, b
    return distance_km(pa, pb) > k_a * rtt_a + t_a + k_b * rtt_b + t_b


def tls_rtt_ms(address, port, timeout=5.0):
    """Measure one round trip to a relay's ORPort, in milliseconds.

    The time runs from sending the TLS ClientHello to the first byte of the
    reply.  The TCP connection is set up before the clock starts, so a SYN
    proxy in front of the relay does not shorten the measurement: the reply
    has to come from the TLS endpoint, the relay itself.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # Only the timing matters, the relay's self-signed certificate is never
    # used for anything.
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # nosec
    incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
    tls = context.wrap_bio(incoming, outgoing)
    try:
        tls.do_handshake()
    except ssl.SSLWantReadError:
        pass
    client_hello = outgoing.read()
    with socket.create_connection((address, port), timeout=timeout) as sock:
        start = time.perf_counter()
        sock.sendall(client_hello)
        reply = sock.recv(1)
        elapsed = time.perf_counter() - start
    if not reply:
        return None
    return elapsed * 1000


def min_rtt_ms(address, port, samples=3, timeout=5.0):
    """Return the smallest of ``samples`` round trips, None if all failed."""
    rtts = []
    for _ in range(samples):
        try:
            rtt = tls_rtt_ms(address, port, timeout)
        except (OSError, ssl.SSLError) as e:
            log.debug("RTT to %s:%s failed: %s", address, port, e)
            continue
        if rtt is not None:
            rtts.append(rtt)
    return min(rtts) if rtts else None
