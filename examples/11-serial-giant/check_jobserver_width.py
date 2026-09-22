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
3. `auto` was never narrower than `off`;
4. `UX-916`: the two `switch-*` arms crossed `style_for_make_version`
   in opposite directions in this one capture, each reading the make
   its own `PATH` selects.

`tests/unit/test_the_workflow_does_not_know_the_payload.py` (`UX-354`)
is why this is a committed module and not a `run:` one-liner.
"""
import json
import sys

#: `lto_preflight_warnings`' own text, matched on its stable middle.
SCRUB_MARK = "scrubbed to recipe -jN"

#: UX-916's two arms, and what each one's staged make implies. One
#: staged make can only exercise one branch, so a capture where these
#: two agree is a switch with one live branch again - which is the
#: defect the row exists to end, not a pass.
SWITCH_ARMS = {
    "switch-4-4.bst": ("GNU Make 4.4", "fifo"),
    "switch-4-2.bst": ("GNU Make 4.2", "fd"),
}


def _row(plane2_path, element):
    report = json.load(open(plane2_path, encoding="utf-8"))
    rows = [row for row in (report.get("per_element_parallelism") or [])
            if row.get("element") == element]
    return rows[0] if rows else None


def check_switch(plane2_path):
    """`UX-916`: the version switch, read off one capture's own report.

    `None`, or the first disagreement as a sentence. Reads
    `sandbox_make` and `auth_style` rather than re-deriving a style
    here: the point of the row is that the report carries them.
    """
    report = json.load(open(plane2_path, encoding="utf-8"))
    rows = {row.get("element"): row
            for row in (report.get("jobserver_decisions") or [])
            if row.get("element") in SWITCH_ARMS}
    missing = sorted(set(SWITCH_ARMS) - set(rows))
    if missing:
        return f"no jobserver_decisions row for {missing}"
    for element, (version, style) in sorted(SWITCH_ARMS.items()):
        row = rows[element]
        print(f"{element}: {row.get('sandbox_make')!r} -> "
              f"{row.get('auth_style')!r} (UX-916)")
        if not (row.get("sandbox_make") or "").startswith(version):
            return (f"{element} was built on {row.get('sandbox_make')!r}, "
                    f"not the {version} its PATH selects")
        if row.get("auth_style") != style:
            return (f"{element} reports auth_style "
                    f"{row.get('auth_style')!r}, not {style!r}")
    styles = {rows[element].get("auth_style") for element in SWITCH_ARMS}
    if len(styles) != len(SWITCH_ARMS):
        return f"both arms took the same branch: {styles}"
    return None


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
          f"resolved width {width if width is not None else 'unknown'}")
    # UX-913's own reading, printed and asserted by neither arm. The
    # resolved width is the real denominator and a peak under it says
    # nothing, so `off`'s measured peak is only the fallback, labelled
    # as one: the auto arm has been seen publishing no width at all,
    # and a missing width must not read as a width nothing exceeded.
    if width is not None:
        verb = "exceeded" if auto_peak > width else "did not exceed"
        print(f"{element}: auto {verb} its resolved width of {width} "
              f"(UX-913)")
    else:
        rel = "wider than" if auto_peak > off_peak else "no wider than"
        print(f"{element}: no resolved width was published, so the only "
              f"reading is that auto ran {rel} off ({auto_peak} against "
              f"{off_peak}) (UX-913)")
    scrubbed = _scrub_lines(auto_log_path)
    if scrubbed:
        return f"the auto capture scrubbed an auth: {scrubbed}"
    if width is not None and off_peak > width:
        return (f"off ran wider than its resolved width for {element!r}: "
                f"{off_peak} > {width}")
    if auto_peak < off_peak:
        return (f"auto ran narrower than off for {element!r}: "
                f"{auto_peak} < {off_peak}")
    return check_switch(auto_path)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    error = check(argv[0], argv[1], argv[2], argv[3])
    if error:
        sys.exit(error)
    return 0


if __name__ == "__main__":
    sys.exit(main())
