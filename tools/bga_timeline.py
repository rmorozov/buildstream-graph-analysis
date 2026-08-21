"""UX-188: one timeline, both planes, one command.

Field feedback: *"recheck that we can produce chrome:tracing compatible
output for plane2 capture — maybe we can make some kind of merge tool
that can merge timeline from plane 1 and plane 2."*

Round 20 ground-truthed it and found the pieces already there:
`bga log-to-chrome` renders a snapshot's Plane 1 log, every extraction
writes `run/chrome_trace.json`, and `bga native-to-chrome combined
<plane1_chrome> <raw_log> <out> --anchor-element X` is precisely the
plane merge the field asked for. Three things kept a user from reaching
it, and none of them was the merge:

1. Snapshots did not retain the raw Plane 2 log the combined mode reads
   (`UX-188` item 1 - they do now, gzipped).
2. Wrong input succeeded silently (item 3 - it refuses now).
3. **Nobody composed it.** Reaching the merged timeline took three
   commands with invented paths, which is the pre-`UX-126` shape that
   `bga snapshot` exists to end.

This is item 2: the one command. It composes what already works rather
than reimplementing it, so the merged trace is byte-identical to what
the three-command form produced.

The anchor: `combined` aligns Plane 2's monotonic clock onto Plane 1's
wall clock using one element that appears in both. Given no
`--anchor-element`, this picks the longest-running element the Plane 2
capture actually traced - the one whose span is least sensitive to a
small alignment error.
"""
import argparse
import gzip
import json
import os
import shutil
import sys
import tempfile
from typing import List, Optional

HELP = """Render one Chrome-trace timeline for a snapshot, both planes in it.

Plane 1's element schedule always; Plane 2's process lanes underneath it
when the snapshot kept its raw trace log (`bga snapshot` keeps one by
default). Open the result with Perfetto (https://ui.perfetto.dev) or
chrome://tracing.
"""

RAW_LOG_NAME = "plane2.log.gz"
WRAPPED_LOG_NAME = "build.log"
RUN_SUBDIR = "run"


def _raw_log(snapshot: str) -> Optional[str]:
    """The snapshot's raw Plane 2 log, compressed or not."""
    for name in (RAW_LOG_NAME, RAW_LOG_NAME[:-3]):
        candidate = os.path.join(snapshot, name)
        if os.path.exists(candidate):
            return candidate
    return None


def _open_raw(path: str):
    return (gzip.open(path, "rt", encoding="utf-8", errors="ignore")
            if path.endswith(".gz")
            else open(path, "r", encoding="utf-8", errors="ignore"))


def pick_anchor(raw_log: str) -> Optional[str]:
    """The element whose Plane 2 span is longest, or None.

    The alignment is a single offset, so any element in both planes
    works; the longest one is chosen because a fixed error in the offset
    is the smallest *share* of its span, and because it is the element a
    reader opening the timeline is most likely looking for.
    """
    from .bst_native_build_tracer import pair_events, parse_trace_lines

    with _open_raw(raw_log) as handle:
        records = pair_events(parse_trace_lines(handle))
    spans = {}
    for record in records:
        element = record.get("element")
        if not element or element == "unknown":
            continue
        start, end = record.get("start_ts"), record.get("end_ts")
        if start is None or end is None:
            continue
        spans[element] = max(spans.get(element, 0), end - start)
    return max(spans, key=spans.get) if spans else None


def render(snapshot: str, output: str,
           anchor_element: Optional[str] = None) -> dict:
    """Write the timeline. Returns what went into it, for the caller to say."""
    from .bst_log_to_chrome_trace import main as plane1_main
    from .native_trace_to_chrome_trace import main as merge_main

    wrapped = os.path.join(snapshot, WRAPPED_LOG_NAME)
    if not os.path.exists(wrapped):
        raise FileNotFoundError(
            f"{snapshot}: no {WRAPPED_LOG_NAME} here. `bga timeline` renders a "
            f"snapshot directory (the one `bga snapshot` created), not a run "
            f"directory - try its parent.")

    scratch = tempfile.mkdtemp(prefix="bga-timeline-")
    try:
        plane1 = os.path.join(scratch, "plane1.json")
        # The existing converters, called rather than reimplemented, so
        # this command cannot drift from the three-command form it
        # replaces.
        code = plane1_main([wrapped, plane1], quiet=True)
        if code:
            raise RuntimeError(f"rendering Plane 1 failed (exit {code})")

        raw = _raw_log(snapshot)
        if raw is None:
            shutil.copyfile(plane1, output)
            return {"planes": ["1"], "anchor": None, "raw_log": None}

        anchor = anchor_element or pick_anchor(raw)
        if anchor is None:
            # A raw log with no element-attributed span: the merge has
            # nothing to align on, so Plane 1 alone is the honest output.
            shutil.copyfile(plane1, output)
            return {"planes": ["1"], "anchor": None, "raw_log": raw,
                    "omitted": "the Plane 2 capture attributes no span to an "
                               "element, so there is nothing to align the two "
                               "planes on"}

        # `combined` reads an uncompressed log; decompress into scratch.
        source = raw
        if raw.endswith(".gz"):
            source = os.path.join(scratch, "plane2.log")
            with _open_raw(raw) as handle, open(source, "w", encoding="utf-8") as out:
                shutil.copyfileobj(handle, out, length=1024 * 1024)

        code = merge_main(["combined", plane1, source, output,
                           "--anchor-element", anchor])
        if code:
            raise RuntimeError(f"merging Plane 2 failed (exit {code})")
        return {"planes": ["1", "2"], "anchor": anchor, "raw_log": raw}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def describe(result: dict, output: str) -> str:
    lines = []
    if result["planes"] == ["1", "2"]:
        lines.append(f"Wrote both planes to {output}, aligned on "
                     f"{result['anchor']}.")
    else:
        lines.append(f"Wrote Plane 1 to {output}.")
        lines.append(
            "  Plane 2 is not in it: " + (
                result.get("omitted")
                or "this snapshot kept no raw trace log. `bga snapshot` keeps "
                   "one by default; a capture taken with --no-keep-raw, or "
                   "before UX-188, has only the processed report."))
    lines.append("  Open it with Perfetto (https://ui.perfetto.dev) or "
                 "chrome://tracing.")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    from bga.help_format import CompactRawHelp

    parser = argparse.ArgumentParser(
        prog="bga timeline", description=HELP,
        formatter_class=lambda prog: CompactRawHelp(prog),
    )
    parser.add_argument(
        "run", nargs="?", default="@last",
        help="The snapshot to render; `@last` by default, same alias grammar "
             "as every other command.")
    parser.add_argument(
        "-o", "--output", default=None, metavar="PATH",
        help="Where to write the trace. Defaults to `timeline.json` inside "
             "the snapshot.")
    parser.add_argument(
        "--anchor-element", default=None, metavar="ELEMENT",
        help="Align the two planes on this element instead of the "
             "longest-running one Plane 2 traced.")
    args = parser.parse_args(argv)

    from bga import run_store

    # The same gate every other command uses: an alias is resolved
    # against the project, and anything else is a path meaning exactly
    # what it says. Reaching for `resolve_snapshot` directly made an
    # explicit path an error, which is not the store's grammar.
    try:
        snapshot = (run_store.resolve_snapshot(args.run, run_store.project_root())
                    if run_store.is_alias(args.run) else args.run)
    except Exception as error:  # noqa: BLE001 - reported, not swallowed
        print(f"Error: {error}", file=sys.stderr)
        return 2

    output = args.output or os.path.join(snapshot, "timeline.json")
    try:
        result = render(snapshot, output, anchor_element=args.anchor_element)
    except (FileNotFoundError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(describe(result, output), file=sys.stderr)
    print(json.dumps({"output": output, **result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
