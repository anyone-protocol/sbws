"""Unit tests for heartbeat"""
import logging

from sbws.lib import heartbeat


def test_register_measured_fpr(conf, caplog):
    """
    Test that checks if the values entered into the function
    register_measured_fpr is inputted into the variable measured_fp.set

    Asserts if the value of measured_fp_set is the same value
    inputted into the function register_measured_fpr which is "123"
    """
    hbeat = heartbeat.Heartbeat(conf.getpath("paths", "state_fname"))
    hbeat.register_measured_fpr("123")
    assert hbeat.measured_fp_set == {"123"}
    caplog.clear()


def test_register_consensus_fprs(conf, caplog):
    """
    Test that checks if the values entered into the function
    register_consensus_fprs is inputted into the variable consensus_fp_set

    Asserts if the value of consensus_fp_set is the same value
    inputted into the function register_consensus_fprs which is ["4","5","6"]
    """
    hbeat = heartbeat.Heartbeat(conf.getpath("paths", "state_fname"))
    hbeat.register_consensus_fprs(["4", "5", "6"])
    assert hbeat.consensus_fp_set == {"4", "5", "6"}
    caplog.clear()


def test_print_heartbeat_message(conf, caplog):
    """
    Test that checks if the print_message function is working as predicted.
    Also, to check if the text is also logged as expected.

    Asserts that the specified text is present in the log
    """
    hbeat = heartbeat.Heartbeat(conf.getpath("paths", "state_fname"))
    hbeat.register_measured_fpr("12")
    hbeat.register_consensus_fprs(["1", "2", "4"])

    caplog.clear()
    hbeat.print_heartbeat_message()
    caplog.set_level(logging.INFO)

    assert hbeat.previous_measurement_percent == 33
    assert "Run None main loops." in caplog.records[0].getMessage()
    assert "Measured in total 1 (33%)" in caplog.records[1].getMessage()
    message2 = "3 relays still not measured"
    assert message2 in caplog.records[2].getMessage()

    caplog.clear()
    newPercent = round(
        len(hbeat.measured_fp_set) / len(hbeat.consensus_fp_set) * 100
    )
    hbeat.previous_measurement_percent = newPercent + 100
    caplog.set_level(logging.WARNING)

    hbeat.print_heartbeat_message()
    messageWarning = "There is no progress measuring new unique relays."
    assert messageWarning in caplog.records[0].getMessage()
