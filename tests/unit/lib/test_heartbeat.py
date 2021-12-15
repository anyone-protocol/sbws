"""Unit tests for heartbeat"""
import logging

from sbws.lib import heartbeat


def test_register_measured_fpr(conf):
    """
    Test that checks if the values entered into the function
    register_measured_fpr is inputted into the variable measured_fp.set

    Asserts if the value of measured_fp_set is the same value
    inputted into the function register_measured_fpr which is "A"
    """
    hbeat = heartbeat.Heartbeat(conf.getpath("paths", "state_fname"))
    hbeat.register_measured_fpr("A")
    hbeat.register_measured_fpr("B")
    assert "A" in hbeat.measured_fp_set
    assert "B" in hbeat.measured_fp_set


def test_register_consensus_fprs(conf):
    """
    Test that checks if the values entered into the function
    register_consensus_fprs is inputted into the variable consensus_fp_set

    Asserts if the value of consensus_fp_set is the same value
    inputted into the function register_consensus_fprs which is ["4","5","6"]
    """
    hbeat = heartbeat.Heartbeat(conf.getpath("paths", "state_fname"))
    hbeat.register_consensus_fprs(["4", "5", "6"])
    assert hbeat.consensus_fp_set == {"4", "5", "6"}


def test_print_heartbeat_message(conf, caplog):
    """
    Test that checks if the print_message function is working as predicted.
    Also, to check if the text is also logged as expected.

    Asserts that the specified text is present in the log
    """
    hbeat = heartbeat.Heartbeat(conf.getpath("paths", "state_fname"))
    hbeat.register_measured_fpr("12")
    hbeat.register_consensus_fprs(["1", "2", "4"])
    hbeat.print_heartbeat_message()

    assert hbeat.previous_measurement_percent == 33
    assert "Run None main loops." in caplog.records[0].getMessage()
    assert "Measured in total 1 (33%" in caplog.records[1].getMessage()
    log_relay_not_measured = "3 relays from the last consensus are not "
    assert log_relay_not_measured in caplog.records[2].getMessage()

    caplog.clear()
    new_percent = round(
        len(hbeat.measured_fp_set) / len(hbeat.consensus_fp_set) * 100
    )
    hbeat.previous_measurement_percent = new_percent + 100
    caplog.set_level(logging.WARNING)

    hbeat.print_heartbeat_message()
    log_no_progress = "There is no progress measuring new unique relays"
    assert log_no_progress in caplog.records[0].getMessage()
