"""timestamps.py unit tests."""

from datetime import datetime, timedelta

from sbws.util.state import State
from sbws.util.timestamps import DateTimeIntSeq, DateTimeSeq


def test_update_datetime_seq(conf):
    now = datetime.utcnow().replace(microsecond=0)
    state = State(conf["paths"]["state_fpath"])
    # Create a list of 6 datetimes that started 6 days in the past.
    dts = [now - timedelta(days=x) for x in range(6, 0, -1)]
    dt_seq = DateTimeSeq(
        dts, state=state, state_key="recent_measurement_attempt"
    )
    new_dts = dt_seq.update()
    # The updated list will not contain the 2 first (left) datetimes and it
    # will have one last timestamp (right).
    assert new_dts[:-1] == dts[2:]
    assert 5 == state.count("recent_measurement_attempt")
    assert 5 == len(dt_seq)


def test_update_datetime_int_seq(conf):
    now = datetime.utcnow().replace(microsecond=0)
    state = State(conf["paths"]["state_fpath"])
    # Create a list of 6 datetimes that started 6 days in the past.
    dts = [[now - timedelta(days=x), 2] for x in range(6, 0, -1)]
    dt_seq = DateTimeIntSeq(
        dts, state=state, state_key="recent_measurement_attempt"
    )
    new_dts = dt_seq.update()
    # The updated list will not contain the 2 first (left) tuples and it
    # will have one last tuple (right).
    # The last tuple have 0 as the integer, instead of 2, so the count will be
    # 2 * 4 = 8
    assert new_dts[:-1] == dts[2:]
    assert 8 == state.count("recent_measurement_attempt")
    # And `len` should return the same.
    assert 8 == len(dt_seq)


def test_last_datetime_seq(conf):
    dt_seq = DateTimeSeq([])
    new_dts = dt_seq.last()
    assert new_dts == datetime.utcnow().replace(microsecond=0) - timedelta(
        hours=1
    )


def test_create_list_datetime_seq(conf):
    now = datetime.utcnow().replace(microsecond=0)
    # Create a list of 6 datetimes that started 6 days in the past.
    dts = [now - timedelta(days=x) for x in range(6, 0, -1)]
    dt_seq = DateTimeSeq(dts)
    new_dts = dt_seq.list()
    assert isinstance(new_dts, list)


def test_create_list_dt_int_seq(conf):
    now = datetime.utcnow().replace(microsecond=0)
    # Create a list of 6 datetimes that started 6 days in the past.
    dts = [now - timedelta(days=x) for x in range(6, 0, -1)]
    dt_int_seq = DateTimeIntSeq(dts)
    new_dt_int_seq = dt_int_seq.list()

    assert isinstance(new_dt_int_seq, list)


def test_last_dt_int_seq(conf):
    dt_seq = DateTimeIntSeq([])
    assert (
        datetime.utcnow().replace(microsecond=0) - timedelta(hours=1)
        == dt_seq.last()
    )
