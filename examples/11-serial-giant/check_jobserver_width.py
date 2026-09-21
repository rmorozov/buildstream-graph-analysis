#!/usr/bin/env python3
"""UX-910: the step's own check, replacing an unbanded `auto < off`
wall assertion that only resolved the sign of this example's own noise.

Width is an integer read from process overlap; a wall on a ~218s build
is not. Three assertions that can fail only on something real, and one
reading printed rather than asserted because `UX-913`'s second gate is
open:

1. the `auto` capture named no scrubbed auth (`UX-883`'s line) - the
   defect `UX-913` found, silent under eight off/auto pairs;
2. `off` held its resolved width, so the baseline is a baseline;
3. `auto` was never narrower than `off`.

`tests/unit/test_the_workflow_does_not_know_the_payload.py` (`UX-354`)
is why this is a committed module and not a `run:` one-liner.
"""
import json
import sys

#: `lto_preflight_warnings`' own text, matched on its stable middle.
SCRUB_MARK = "scrubbed to recipe -jN"


def _row(plane2_path, element):
    report = json.load(open(plane2_path, encoding="utf-8"))
    rows = [row for row in (report.get("per_element_parallelism") or [])
            if row.get("element") == element]
    return rows[0] if rows else None


def _scrub_lines(log_path):
    with open(log_path, encoding="utf-8", errors="replace") as handle:
        return [line.strip() for line in handle if SCRUB_MARK in line]


def check(off_path, auto_path, element, auto_log_path):
    off, auto = _row(off_path, element), _row(auto_path, element)
    if off is None or auto is None:
        return (f"no per_element_parallelism row for {element!r}: "
                f"off={off}, auto={auto}")
    off_peak = off.get("peak_work_concurrency") or 0
    auto_peak = auto.get("peak_work_concurrency") or 0
    width = off.get("resolved_jobs")
    print(f"{element}: off peak {off_peak}, auto peak {auto_peak}, "
          f"resolved width {width}")
    # UX-913's own reading, printed by both arms and asserted by
    # neither: the pool is reachable here and still not drawn from.
    granted = width is not None and auto_peak > width
    print(f"{element}: auto {'exceeded' if granted else 'did not exceed'} "
          f"its resolved width (UX-913)")
    scrubbed = _scrub_lines(auto_log_path)
    if scrubbed:
        return f"the auto capture scrubbed an auth: {scrubbed}"
    if width is not None and off_peak > width:
        return (f"off ran wider than its resolved width for {element!r}: "
                f"{off_peak} > {width}")
    if auto_peak < off_peak:
        return (f"auto ran narrower than off for {element!r}: "
                f"{auto_peak} < {off_peak}")
    return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    error = check(argv[0], argv[1], argv[2], argv[3])
    if error:
        sys.exit(error)
    return 0


if __name__ == "__main__":
    sys.exit(main())
