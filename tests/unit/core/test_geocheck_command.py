import json
import os

import pytest
from stem.descriptor import parse_file

import sbws.core.geocheck
from sbws.lib import geocheck

FRANKFURT = (50.11, 8.68)
JOHANNESBURG = (-26.20, 28.05)


def label(coordinates, country=None, as_=None):
    return {"coordinates": coordinates, "country": country, "as": as_}


def test_check_relays_verdicts():
    relays = [
        ("A" * 40, "near", "10.0.0.1", 9001),
        ("B" * 40, "liar", "10.0.0.2", 9001),
        ("C" * 40, "down", "10.0.0.3", 9001),
        ("D" * 40, "nolabel", "10.0.0.4", 9001),
    ]
    labels = {
        "A" * 40: label(FRANKFURT),
        "B" * 40: label(JOHANNESBURG, "ZA", "AS64500 Example"),
        "C" * 40: label(FRANKFURT),
    }
    rtts = {"10.0.0.1": 1.0, "10.0.0.2": 3.0, "10.0.0.3": None}
    entries = sbws.core.geocheck.check_relays(
        relays,
        labels,
        FRANKFURT,
        rtt=lambda address, port, samples, timeout: rtts[address],
    )
    verdicts = {e["nickname"]: e["verdict"] for e in entries}
    assert verdicts == {
        "near": "possible",
        "liar": "impossible",
        "down": "unreachable",
        "nolabel": "unlabeled",
    }
    liar = entries[1]
    assert liar["rtt_ms"] == 3.0
    assert liar["excess_km"] == round(liar["label_distance_km"] - 350)
    # In vacuum 3 ms reach 450 km, plus the 50 km tolerance.
    assert liar["vacuum_excess_km"] == round(liar["label_distance_km"] - 500)
    assert liar["label_country"] == "ZA"
    assert liar["label_as"] == "AS64500 Example"


def test_check_relays_rechecks_labels_close_to_the_reach():
    # The label is 801 km from the scanner.
    scanner, near_reach = (0.0, 0.0), (0.0, 7.2)
    calls = []

    def rtt(address, port, samples, timeout):
        calls.append(samples)
        # A noisy first round trip, a faster one with more samples.
        return 7.6 if samples == 3 else 7.0

    entries = sbws.core.geocheck.check_relays(
        [("A" * 40, "close", "10.0.0.1", 9001)],
        {"A" * 40: label(near_reach)},
        scanner,
        rtt=rtt,
    )
    # 7.6 ms reach 810 km: possible, 9 km inside the reach.  Measured again,
    # 7.0 ms reach 750 km: impossible.
    assert calls == [3, 10]
    assert entries[0]["rechecked"]
    assert entries[0]["rtt_ms"] == 7.0
    assert entries[0]["verdict"] == "impossible"


def test_check_relays_does_not_recheck_far_from_the_reach():
    calls = []

    def rtt(address, port, samples, timeout):
        calls.append(samples)
        return 2.0  # reaches 250 km, the label is 250 km inside the reach

    entries = sbws.core.geocheck.check_relays(
        [("A" * 40, "near", "10.0.0.1", 9001)],
        {"A" * 40: label(FRANKFURT)},
        FRANKFURT,
        rtt=rtt,
    )
    assert calls == [3]
    assert "rechecked" not in entries[0]


def test_load_labels(tmpdir):
    path = tmpdir.join("fingerprint-map.json")
    path.write(
        json.dumps(
            {
                "a"
                * 40: {
                    "hexId": "841f",
                    "coordinates": list(FRANKFURT),
                    "countryCode": "DE",
                    "asNumber": "64500",
                    "asName": "Example",
                },
                "b" * 40: {"hexId": "841f"},
                "c" * 40: {"coordinates": [1.0, 2.0]},
            }
        )
    )
    assert sbws.core.geocheck.load_labels(path.strpath) == {
        "A" * 40: label(FRANKFURT, "DE", "AS64500 Example"),
        "C" * 40: label((1.0, 2.0)),
    }


def test_summarize():
    entries = [
        {"verdict": "impossible", "vacuum_excess_km": 10, "label_as": "AS1"},
        {"verdict": "impossible", "vacuum_excess_km": -5, "label_as": "AS1"},
        {"verdict": "impossible", "vacuum_excess_km": 1, "label_as": None},
        {"verdict": "possible", "vacuum_excess_km": -900, "label_as": "AS2"},
    ]
    summary = sbws.core.geocheck.summarize(entries)
    assert summary["counts"] == {"impossible": 3, "possible": 1}
    assert summary["impossible_in_vacuum"] == 2
    assert summary["impossible_by_label_as"] == {"AS1": 2, "unknown": 1}


def _report(scanner, measurements):
    """A geocheck report with {fingerprint: rtt_ms}, labels in Frankfurt."""
    entries = []
    for fp, rtt_ms in measurements.items():
        entry = {
            "fingerprint": fp,
            "nickname": fp[:4],
            "address": "10.0.0.1",
            "or_port": 9001,
            "label": list(FRANKFURT),
        }
        sbws.core.geocheck.judge_rtt(
            entry, scanner, rtt_ms, geocheck.KM_PER_MS, geocheck.TOLERANCE_KM
        )
        entries.append(entry)
    return {
        "scanner": list(scanner),
        "km_per_ms": geocheck.KM_PER_MS,
        "tolerance_km": geocheck.TOLERANCE_KM,
        "relays": entries,
    }


def test_merge_reports():
    frankfurt = _report(FRANKFURT, {"A" * 40: 1.0, "B" * 40: 1.0})
    johannesburg = _report(
        JOHANNESBURG,
        # A: in Frankfurt.  B: 40 ms can not reach Frankfurt from
        # Johannesburg, and 1 + 40 ms can not be true together.
        {"A" * 40: 90.0, "B" * 40: 40.0, "C" * 40: 90.0},
    )
    entries, contradictions = sbws.core.geocheck.merge_reports(
        [frankfurt, johannesburg]
    )
    verdicts = {e["fingerprint"][0]: e["verdict"] for e in entries}
    assert verdicts == {"A": "possible", "B": "impossible", "C": "possible"}
    assert contradictions == {"0-1": 1}
    b = next(e for e in entries if e["fingerprint"] == "B" * 40)
    assert [m["report"] for m in b["scanners"]] == [0, 1]
    assert b["excess_km"] == max(m["excess_km"] for m in b["scanners"])


def test_merge_reports_judges_the_last_label():
    # Day 1: labeled in Johannesburg, 1 ms from Frankfurt: impossible.
    # Day 2: the label was corrected to Frankfurt.
    day1 = _report(FRANKFURT, {"A" * 40: 1.0})
    day1["relays"][0]["label"] = list(JOHANNESBURG)
    sbws.core.geocheck.judge_rtt(
        day1["relays"][0],
        FRANKFURT,
        1.0,
        geocheck.KM_PER_MS,
        geocheck.TOLERANCE_KM,
    )
    assert day1["relays"][0]["verdict"] == "impossible"
    day2 = _report(FRANKFURT, {"A" * 40: 1.0})
    entries, _ = sbws.core.geocheck.merge_reports([day1, day2])
    assert entries[0]["label"] == list(FRANKFURT)
    assert entries[0]["verdict"] == "possible"
    assert [m["verdict"] for m in entries[0]["scanners"]] == ["possible"] * 2


def test_main_writes_report(parser, conf, root_data_path, tmpdir, monkeypatch):
    consensus = os.path.join(root_data_path, "2020-02-29-10-00-00-consensus")
    fingerprints = [r.fingerprint for r in parse_file(consensus)]
    labels = tmpdir.join("fingerprint-map.json")
    labels.write(
        json.dumps(
            {
                fingerprints[0]: {
                    "coordinates": list(JOHANNESBURG),
                    "asNumber": "64500",
                    "asName": "Example",
                },
                fingerprints[1]: {"coordinates": list(FRANKFURT)},
            }
        )
    )
    monkeypatch.setattr(
        geocheck, "min_rtt_ms", lambda address, port, samples, timeout: 2.0
    )
    output = tmpdir.join("report.json")
    args = parser.parse_args(
        [
            "geocheck",
            "--latitude",
            str(FRANKFURT[0]),
            "--longitude",
            str(FRANKFURT[1]),
            "--labels",
            labels.strpath,
            "--consensus",
            consensus,
            "--output",
            output.strpath,
        ]
    )
    sbws.core.geocheck.main(args, conf)
    report = json.loads(output.read())
    assert report["scanner"] == list(FRANKFURT)
    assert report["counts"] == {
        "impossible": 1,
        "possible": 1,
        "unlabeled": len(fingerprints) - 2,
    }
    assert report["impossible_in_vacuum"] == 1
    assert report["impossible_by_label_as"] == {"AS64500 Example": 1}
    impossible = [e for e in report["relays"] if e["verdict"] == "impossible"]
    assert impossible[0]["fingerprint"] == fingerprints[0]

    merged = tmpdir.join("merged.json")
    args = parser.parse_args(
        [
            "geocheck",
            "--merge",
            output.strpath,
            output.strpath,
            "--output",
            merged.strpath,
        ]
    )
    sbws.core.geocheck.main(args, conf)
    report = json.loads(merged.read())
    assert [m["report"] for m in report["merged"]] == [output.strpath] * 2
    assert report["counts"] == {
        "impossible": 1,
        "possible": 1,
        "unlabeled": len(fingerprints) - 2,
    }
    assert report["contradictions"] == {}


def test_main_needs_the_scanner_position(parser, conf):
    args = parser.parse_args(["geocheck"])
    with pytest.raises(SystemExit):
        sbws.core.geocheck.main(args, conf)
