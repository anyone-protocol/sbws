import socket
import threading
import time

import pytest

from sbws.lib import geocheck

FRANKFURT = (50.11, 8.68)
JOHANNESBURG = (-26.20, 28.05)


def test_distance_km():
    assert geocheck.distance_km((0, 0), (0, 1)) == pytest.approx(111.2, 0.01)
    assert geocheck.distance_km(FRANKFURT, FRANKFURT) == 0
    assert geocheck.distance_km(FRANKFURT, JOHANNESBURG) == pytest.approx(
        8698, abs=1
    )


def test_label_excess_km():
    # 5 ms reaches 100 * 5 + 50 = 550 km, Johannesburg is 8,698 km away.
    excess = geocheck.label_excess_km(FRANKFURT, JOHANNESBURG, 5)
    assert excess == pytest.approx(8148, abs=1)
    # 90 ms reaches 9,050 km.
    assert geocheck.label_excess_km(FRANKFURT, JOHANNESBURG, 90) < 0
    # A label at the scanner is never impossible.
    assert geocheck.label_excess_km(FRANKFURT, FRANKFURT, 0) < 0


def test_delay_can_not_make_a_label_impossible():
    """A larger round trip only makes the excess smaller."""
    excesses = [
        geocheck.label_excess_km(FRANKFURT, JOHANNESBURG, rtt)
        for rtt in (0, 1, 10, 100)
    ]
    assert excesses == sorted(excesses, reverse=True)


def test_contradicts():
    # Frankfurt and Johannesburg are 8,698 km apart.
    def measure(scanner, rtt):
        return (scanner, rtt, geocheck.KM_PER_MS, geocheck.TOLERANCE_KM)

    # 40 + 40 ms reach 4,050 + 4,050 km: no relay can be that close to both.
    assert geocheck.contradicts(
        measure(FRANKFURT, 40), measure(JOHANNESBURG, 40)
    )
    # 1 + 90 ms reach 150 + 9,050 km: a relay in Frankfurt.
    assert not geocheck.contradicts(
        measure(FRANKFURT, 1), measure(JOHANNESBURG, 90)
    )


def _server(reply, delay):
    """Listen on localhost, answer the first bytes after ``delay`` s."""
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()

    def serve():
        conn, _ = listener.accept()
        with conn:
            conn.recv(4096)
            time.sleep(delay)
            if reply:
                conn.sendall(reply)
        listener.close()

    threading.Thread(target=serve, daemon=True).start()
    return listener.getsockname()


def test_tls_rtt_ms_times_the_reply():
    address, port = _server(b"\x16", 0.05)
    rtt = geocheck.tls_rtt_ms(address, port, timeout=2)
    assert 50 <= rtt < 1000


def test_tls_rtt_ms_closed_without_reply():
    address, port = _server(b"", 0)
    assert geocheck.tls_rtt_ms(address, port, timeout=2) is None


def test_min_rtt_ms_unreachable():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    address, port = listener.getsockname()
    listener.close()
    assert geocheck.min_rtt_ms(address, port, samples=2, timeout=1) is None
