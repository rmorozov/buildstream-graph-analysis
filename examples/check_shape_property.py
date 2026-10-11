#!/usr/bin/env python3
"""UX-1132: each new shape's designed property, read off its capture.

    two-giants   PLANE2 TRACE A B    both wider than one job, BUILD spans overlap
    wide-chain   PLANE2 E1 E2 ...    every chain element wider than one job
    memory-giant PLANE2 E FLOOR_MB   the element's peak RSS per job >= FLOOR_MB
    late-peak    TRACE_LOG E K       what ends after E's last cc1 peaks >= K x its largest cc1

Prints one line (the step's `::notice::`) and exits 1 when the property
does not hold. A committed module, not a `run:` one-liner (`UX-354`).
"""

import gzip
import json
import os
import sys


def _plane2(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _width(report, element):
    rows = [r for r in report.get("per_element_parallelism") or [] if r.get("element") == element]
    return rows[0].get("peak_work_concurrency") if rows else None


def _build_span(trace_path, element):
    """`(start_us, end_us)` of the element's BUILD task in Plane 1."""
    with open(trace_path, encoding="utf-8") as handle:
        spans = json.load(handle).get("spans") or []
    for span in spans:
        uid, kind = (span.get("task_key") or "").split("|")[:2]
        if kind == "BUILD" and (uid == element or uid.endswith(":" + element)):
            return span["ts_us"], span["ts_us"] + span["dur_us"]
    return None


def two_giants(plane2, trace, first, second):
    report = _plane2(plane2)
    widths = {e: _width(report, e) for e in (first, second)}
    spans = {e: _build_span(trace, e) for e in (first, second)}
    overlap_s = None
    if all(spans.values()):
        overlap_s = (min(spans[first][1], spans[second][1]) - max(spans[first][0], spans[second][0])) / 1e6
    ok = all((w or 0) > 1 for w in widths.values()) and overlap_s is not None and overlap_s > 0
    line = " ".join(f"{e}:width={w}" for e, w in widths.items()) + f" overlap={overlap_s}s"
    return ok, line


def wide_chain(plane2, *elements):
    report = _plane2(plane2)
    widths = {e: _width(report, e) for e in elements}
    ok = bool(widths) and all((w or 0) > 1 for w in widths.values())
    return ok, " ".join(f"{e}:width={w}" for e, w in widths.items())


def memory_giant(plane2, element, floor_mb):
    report = _plane2(plane2)
    entry = ((report.get("peak_memory") or {}).get("per_element") or {}).get(element) or {}
    peak_kb = entry.get("peak_rss_kb")
    memory = (report.get("jobserver_pool") or {}).get("memory") or {}
    peak_mb = None if peak_kb is None else round(peak_kb / 1024)
    ok = peak_mb is not None and peak_mb >= float(floor_mb)
    line = (
        f"{element}:peak_rss_per_job={peak_mb}MB floor={floor_mb}MB width={_width(report, element)} "
        f"psi_memory_withdraws={memory.get('psi_memory_withdraws')} psi_memory={memory.get('psi_memory_present')}"
    )
    return ok, line


def _ends(trace_log, element):
    """`(ts, maxrss_kb, binary)` per hook END line of `element` (UX-1284)."""
    opener = gzip.open if trace_log.endswith(".gz") else open
    rows = []
    with opener(trace_log, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.startswith("END "):
                continue
            head, _, cmd = line.rstrip("\n").partition(" cmd=")
            fields = dict(token.split("=", 1) for token in head.split(" ")[1:] if "=" in token)
            if fields.get("element") != element or "maxrss_kb" not in fields:
                continue
            rows.append((float(fields["ts"]), int(fields["maxrss_kb"]), os.path.basename(cmd.split(" ", 1)[0])))
    return rows


def late_peak(trace_log, element, k):
    rows = _ends(trace_log, element)
    compiles = [r for r in rows if r[2] in ("cc1", "cc1plus")]
    last_cc1 = max((r[0] for r in compiles), default=None)
    late = [r for r in rows if last_cc1 is not None and r[0] > last_cc1]
    cc1_kb = max((r[1] for r in compiles), default=0)
    peak = max(late, key=lambda r: r[1], default=(0, 0, "-"))
    ok = cc1_kb > 0 and peak[1] >= float(k) * cc1_kb
    ratio = round(peak[1] / cc1_kb, 2) if cc1_kb else None
    line = f"{element}:cc1_peak={cc1_kb // 1024}MB late_peak={peak[1] // 1024}MB({peak[2]}) ratio={ratio} k={k}"
    return ok, line


CHECKS = {"two-giants": two_giants, "wide-chain": wide_chain, "memory-giant": memory_giant, "late-peak": late_peak}


def main(argv):
    if len(argv) < 3 or argv[1] not in CHECKS:
        print(__doc__, file=sys.stderr)
        return 2
    ok, line = CHECKS[argv[1]](*argv[2:])
    print(("OK " if ok else "FAIL ") + argv[1] + ": " + line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
