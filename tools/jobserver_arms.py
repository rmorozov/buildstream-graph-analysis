"""UX-905: read an `off` and an `auto` Plane 2 report of one build as a pair.

Width is the signal and the wall is not (UX-910): the table prints each
element's peak work concurrency under both arms beside its work count,
so a doubled width at equal work reads as a drawn pool. The one
assertion is that the `auto` arm's mode ran and the `off` arm's did not:
a pair whose arms are mislabelled, or whose mode was silently absent,
is not a pair.

    python3 -m tools.jobserver_arms OFF_REPORT AUTO_REPORT
"""
import json
import sys
from collections import Counter


def _load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _widths(report):
    return {row["element"]: row for row in report.get("per_element_parallelism") or []}


def arms(off, auto):
    """The pair's reading, and the problems that make it not a pair."""
    problems = []
    if off.get("jobserver") is not None:
        problems.append(f"the off arm ran a jobserver of {off['jobserver']}")
    if auto.get("jobserver") is None:
        problems.append("the auto arm ran no jobserver")
    elif not auto.get("jobserver_decisions"):
        problems.append("the auto arm recorded no per-sandbox decision")
    off_rows, auto_rows = _widths(off), _widths(auto)
    rows = []
    for element in sorted(set(off_rows) | set(auto_rows)):
        o, a = off_rows.get(element, {}), auto_rows.get(element, {})
        rows.append({
            "element": element,
            "off_peak": o.get("peak_work_concurrency"),
            "auto_peak": a.get("peak_work_concurrency"),
            "requested": o.get("requested_jobs"),
            "off_work": o.get("work_process_count"),
            "auto_work": a.get("work_process_count"),
        })
    decisions = Counter((d.get("decision"), d.get("policy"))
                        for d in auto.get("jobserver_decisions") or [])
    return {
        "problems": problems, "rows": rows,
        "decisions": sorted(decisions.items(), key=lambda kv: -kv[1]),
        "pool": auto.get("jobserver_pool"), "auth": auto.get("jobserver_auth"),
        "wall_s": (off.get("wall_span_s"), auto.get("wall_span_s")),
    }


def render(reading):
    out = [f"{'element':<52} {'req':>3} {'off peak':>8} {'auto peak':>9}"
           f" {'off work':>8} {'auto work':>9}"]
    for r in reading["rows"]:
        out.append(f"{r['element']:<52} {r['requested'] or '?':>3}"
                   f" {r['off_peak'] if r['off_peak'] is not None else '-':>8}"
                   f" {r['auto_peak'] if r['auto_peak'] is not None else '-':>9}"
                   f" {r['off_work'] if r['off_work'] is not None else '-':>8}"
                   f" {r['auto_work'] if r['auto_work'] is not None else '-':>9}")
    out.append(f"auth: {reading['auth']}  pool: {json.dumps(reading['pool'], sort_keys=True)}")
    for (decision, policy), count in reading["decisions"]:
        out.append(f"decision {decision} policy {policy}: {count}")
    off_wall, auto_wall = reading["wall_s"]
    out.append(f"wall_span_s off={off_wall} auto={auto_wall} (a reading, not a verdict)")
    out.extend(f"NOT A PAIR: {p}" for p in reading["problems"])
    return "\n".join(out)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: python3 -m tools.jobserver_arms OFF_REPORT AUTO_REPORT", file=sys.stderr)
        return 2
    reading = arms(_load(argv[0]), _load(argv[1]))
    print(render(reading))
    return 1 if reading["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
