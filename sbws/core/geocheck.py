"""Report relays whose geolocation label is physically impossible."""

import json
import logging
import os
from argparse import ArgumentDefaultsHelpFormatter
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from itertools import combinations

import requests
from stem.descriptor import parse_file

from sbws.globals import fail_hard
from sbws.lib import geocheck

log = logging.getLogger(__name__)

FINGERPRINT_MAP_URL = "https://api.ec.anyone.tech/fingerprint-map"


def gen_parser(sub):
    d = (
        "Measure the round trip time from this scanner to every relay in the "
        "consensus and report the relays whose geolocation label is farther "
        "away than light in fiber travels in that time.  With --merge, "
        "combine the reports of several scanners instead of measuring."
    )
    p = sub.add_parser(
        "geocheck",
        description=d,
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--latitude",
        type=float,
        help="Scanner latitude, required unless --merge is given",
    )
    p.add_argument(
        "--longitude",
        type=float,
        help="Scanner longitude, required unless --merge is given",
    )
    p.add_argument(
        "--labels",
        default=FINGERPRINT_MAP_URL,
        help="URL or path of the fingerprint map holding the relay labels",
    )
    p.add_argument(
        "--consensus",
        help="Consensus file, cached-consensus in the tor datadir by default",
    )
    p.add_argument(
        "--output",
        help="Report file, geocheck/geocheck-<time>.json in sbws home by "
        "default",
    )
    p.add_argument(
        "--samples", type=int, default=3, help="Round trips per relay"
    )
    p.add_argument(
        "--timeout", type=float, default=5.0, help="Seconds per round trip"
    )
    p.add_argument(
        "--workers", type=int, default=32, help="Relays measured in parallel"
    )
    p.add_argument(
        "--km-per-ms",
        type=float,
        default=geocheck.KM_PER_MS,
        help="Largest distance per ms of round trip time",
    )
    p.add_argument(
        "--tolerance-km",
        type=float,
        default=geocheck.TOLERANCE_KM,
        help="Distance added to the reach before a label is impossible; "
        "use more if the scanner position is only roughly known",
    )
    p.add_argument(
        "--recheck-km",
        type=float,
        default=200.0,
        help="Measure again, with --recheck-samples round trips, the possible "
        "labels this close to the reach; 0 disables",
    )
    p.add_argument(
        "--recheck-samples",
        type=int,
        default=10,
        help="Round trips per relay when measuring again",
    )
    p.add_argument(
        "--merge",
        nargs="+",
        metavar="REPORT",
        help="Combine these geocheck reports, of different scanners or "
        "days, into one report instead of measuring",
    )


def load_labels(source):
    """Return {fingerprint: label} from a fingerprint map.

    A label is a dict with the ``coordinates`` (latitude, longitude) and,
    when the map has them, the ``country`` code and the ``as`` of the address.
    """
    if source.startswith(("http://", "https://")):
        response = requests.get(source, timeout=60)
        response.raise_for_status()
        data = response.json()
    else:
        with open(source) as f:
            data = json.load(f)
    labels = {}
    for fp, entry in data.items():
        if not entry.get("coordinates"):
            continue
        as_number, as_name = entry.get("asNumber"), entry.get("asName")
        labels[fp.upper()] = {
            "coordinates": tuple(entry["coordinates"]),
            "country": entry.get("countryCode"),
            "as": (
                f"AS{as_number} {as_name or ''}".strip() if as_number else None
            ),
        }
    return labels


def judge_rtt(entry, scanner, rtt_ms, km_per_ms, tolerance_km):
    """Fill ``entry`` with the verdict for a round trip of ``rtt_ms``."""
    label = tuple(entry["label"])
    excess = geocheck.label_excess_km(
        scanner, label, rtt_ms, km_per_ms, tolerance_km
    )
    entry.update(
        rtt_ms=round(rtt_ms, 3),
        label_distance_km=round(geocheck.distance_km(scanner, label)),
        excess_km=round(excess),
        vacuum_excess_km=round(
            geocheck.label_excess_km(
                scanner,
                label,
                rtt_ms,
                geocheck.VACUUM_KM_PER_MS,
                tolerance_km,
            )
        ),
        verdict="impossible" if excess > 0 else "possible",
    )


def check_relays(
    relays,
    labels,
    scanner,
    rtt=None,
    samples=3,
    timeout=5.0,
    workers=32,
    km_per_ms=geocheck.KM_PER_MS,
    tolerance_km=geocheck.TOLERANCE_KM,
    recheck_km=200.0,
    recheck_samples=10,
):
    """Measure and judge each relay.

    :param relays: (fingerprint, nickname, address, or_port) tuples
    :param labels: {fingerprint: label}, see :func:`load_labels`
    :param scanner: (latitude, longitude) of this scanner
    :param rtt: function (address, or_port, samples, timeout) -> ms or None,
        :func:`sbws.lib.geocheck.min_rtt_ms` by default
    :param recheck_km: a possible label at most this far inside the reach is
        measured again with ``recheck_samples`` round trips.  Noise only makes
        round trips longer, so the smaller of the two can only reveal an
        impossible label, never make a correct one look impossible.
    :returns: one dict per relay, with ``verdict`` "impossible", "possible",
        "unreachable" or "unlabeled"
    """
    rtt = rtt or geocheck.min_rtt_ms

    def judge(relay):
        fingerprint, nickname, address, or_port = relay
        entry = {
            "fingerprint": fingerprint,
            "nickname": nickname,
            "address": address,
            "or_port": or_port,
        }
        label = labels.get(fingerprint)
        if label is None:
            entry["verdict"] = "unlabeled"
            return entry
        entry.update(
            label=list(label["coordinates"]),
            label_country=label.get("country"),
            label_as=label.get("as"),
        )
        rtt_ms = rtt(address, or_port, samples, timeout)
        if rtt_ms is None:
            entry["verdict"] = "unreachable"
            return entry
        judge_rtt(entry, scanner, rtt_ms, km_per_ms, tolerance_km)
        if recheck_km and -recheck_km < entry["excess_km"] <= 0:
            again = rtt(address, or_port, recheck_samples, timeout)
            entry["rechecked"] = True
            if again is not None and again < rtt_ms:
                judge_rtt(entry, scanner, again, km_per_ms, tolerance_km)
        return entry

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(judge, relays))


def summarize(entries):
    """Return the verdict counts and where the impossible labels point."""
    impossible = [e for e in entries if e["verdict"] == "impossible"]
    return {
        "counts": dict(Counter(e["verdict"] for e in entries)),
        # Impossible even if the round trip ran at the speed of light in
        # vacuum: no network can explain these labels.
        "impossible_in_vacuum": sum(
            e.get("vacuum_excess_km", 0) > 0 for e in impossible
        ),
        "impossible_by_label_as": dict(
            Counter(e.get("label_as") or "unknown" for e in impossible)
        ),
        "impossible_by_label_country": dict(
            Counter(e.get("label_country") or "unknown" for e in impossible)
        ),
    }


def merge_reports(reports):
    """Combine the reports of several scanners.

    A label is impossible when any scanner finds it impossible.  Two
    measurements of one relay contradict each other when no point is within
    reach of both scanners: physically this can not happen, so one of the
    scanner positions in the reports is wrong (or the relay address is
    anycast).  This only catches large errors, like swapped latitude and
    longitude, and no contradiction does not prove the positions right.

    Reports of the same scanner on different days can be merged too: a short
    round trip can not be faked, so one is enough.  Every round trip is judged
    again against the label of the last report that has one, so a label that
    changed between the reports is never reported for an older label's fault.

    :returns: (entries, {"i-j": number of relays the reports i and j
        contradict on})
    """
    relays = {}
    for i, report in enumerate(reports):
        km_per_ms = report.get("km_per_ms", geocheck.KM_PER_MS)
        tolerance_km = report.get("tolerance_km", geocheck.TOLERANCE_KM)
        for e in report["relays"]:
            merged = relays.setdefault(
                e["fingerprint"],
                {
                    k: e[k]
                    for k in ("fingerprint", "nickname", "address", "or_port")
                },
            )
            for k in ("label", "label_country", "label_as"):
                if k in e:
                    merged[k] = e[k]
            if "rtt_ms" in e:
                merged.setdefault("scanners", []).append(
                    {
                        "report": i,
                        "rtt_ms": e["rtt_ms"],
                        "_measure": (
                            tuple(report["scanner"]),
                            e["rtt_ms"],
                            km_per_ms,
                            tolerance_km,
                        ),
                    }
                )
    contradictions = Counter()
    for merged in relays.values():
        measured = merged.get("scanners", [])
        if not measured:
            merged["verdict"] = (
                "unreachable" if "label" in merged else "unlabeled"
            )
            continue
        for a, b in combinations(measured, 2):
            if geocheck.contradicts(a["_measure"], b["_measure"]):
                contradictions[f"{a['report']}-{b['report']}"] += 1
        for m in measured:
            scanner, rtt_ms, km_per_ms, tolerance_km = m.pop("_measure")
            m["label"] = merged["label"]
            judge_rtt(m, scanner, rtt_ms, km_per_ms, tolerance_km)
            del m["label"], m["label_distance_km"]
        merged["excess_km"] = max(m["excess_km"] for m in measured)
        merged["vacuum_excess_km"] = max(
            m["vacuum_excess_km"] for m in measured
        )
        merged["verdict"] = (
            "impossible" if merged["excess_km"] > 0 else "possible"
        )
    return list(relays.values()), dict(contradictions)


def write_report(report, args, conf, now):
    output = args.output or os.path.join(
        conf.getpath("paths", "sbws_home"),
        "geocheck",
        now.strftime("geocheck-%Y%m%dT%H%M%SZ.json"),
    )
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "w") as f:
        json.dump(report, f, indent=1)
    log.info(
        "Verdicts %s, %d impossible even in vacuum, report in %s",
        report["counts"],
        report["impossible_in_vacuum"],
        output,
    )


def main_merge(args, conf):
    reports = []
    for path in args.merge:
        with open(path) as f:
            reports.append(json.load(f))
    entries, contradictions = merge_reports(reports)
    for pair, n in sorted(contradictions.items()):
        i, j = map(int, pair.split("-"))
        log.warning(
            "%s and %s contradict each other on %d relays: one of the "
            "scanner positions is wrong.",
            args.merge[i],
            args.merge[j],
            n,
        )
    now = datetime.now(timezone.utc)
    report = {
        "time": now.isoformat(),
        "merged": [
            {
                "report": path,
                "time": r.get("time"),
                "scanner": r["scanner"],
                "km_per_ms": r.get("km_per_ms", geocheck.KM_PER_MS),
                "tolerance_km": r.get("tolerance_km", geocheck.TOLERANCE_KM),
            }
            for path, r in zip(args.merge, reports)
        ],
        "contradictions": contradictions,
        **summarize(entries),
        "relays": entries,
    }
    write_report(report, args, conf, now)


def main(args, conf):
    if args.merge:
        return main_merge(args, conf)
    if args.latitude is None or args.longitude is None:
        fail_hard("--latitude and --longitude are required to measure.")
    consensus = args.consensus or os.path.join(
        conf.getpath("tor", "datadir"), "cached-consensus"
    )
    relays = [
        (r.fingerprint, r.nickname, r.address, r.or_port)
        for r in parse_file(consensus)
    ]
    labels = load_labels(args.labels)
    scanner = (args.latitude, args.longitude)
    log.info("Checking the labels of %d relays.", len(relays))
    entries = check_relays(
        relays,
        labels,
        scanner,
        samples=args.samples,
        timeout=args.timeout,
        workers=args.workers,
        km_per_ms=args.km_per_ms,
        tolerance_km=args.tolerance_km,
        recheck_km=args.recheck_km,
        recheck_samples=args.recheck_samples,
    )
    for e in entries:
        if e["verdict"] == "impossible":
            log.warning(
                "%s (%s) label is %d km away, %.1f ms reaches %d km.",
                e["nickname"],
                e["fingerprint"],
                e["label_distance_km"],
                e["rtt_ms"],
                e["label_distance_km"] - e["excess_km"],
            )
    now = datetime.now(timezone.utc)
    report = {
        "time": now.isoformat(),
        "scanner": list(scanner),
        "km_per_ms": args.km_per_ms,
        "tolerance_km": args.tolerance_km,
        **summarize(entries),
        "relays": entries,
    }
    write_report(report, args, conf, now)
