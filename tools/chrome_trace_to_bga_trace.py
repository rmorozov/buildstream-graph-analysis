#!/usr/bin/env python3
"""Convert Chrome Trace Event JSON (as emitted by tools/bst_log_to_chrome_trace.py)
into trace/v9 JSON (Part 32.3) - the second half of the real ingestion
pipeline's trace side (see docs/spec/ingestion-pipeline.md).

This is a separate, general-purpose tool - not the same as
tests/fixtures/synthetic_multi_subproject/adapter.py, which is
fixture-specific: it recovers a BuildStream task's *kind* by pattern-
matching the synthetic model's own invented phase-message text
("Running build commands" -> BUILD), which is not how real BuildStream
logs look at all. A real BuildStream log's START/SUCCESS message text is
either a log file path (for the outer per-task bracket) or a short
internal-progress phrase ("Staging sources") for nested sub-phases -
never a phase description - confirmed against a real, installed
BuildStream 2.7.0 build (see docs/spec/ingestion-pipeline.md). This tool
instead reads the `action` field bst_log_to_chrome_trace.py now records
directly in each bst-builder event's `args` (added specifically to make
this conversion possible without message-text guessing), which is
BuildStream's own real action word (track/fetch/build/pull/push) taken
straight from the log line's own `[hash][action:element]` bracket.
"""
import argparse
import json
from collections import defaultdict
from typing import List, Sequence, Tuple

ACTION_TO_KIND = {
    "track": "TRACK",
    "fetch": "FETCH",
    "pull": "PULL",
    "build": "BUILD",
    "push": "PUSH",
}

# Part 27's critical-path resource-mix table groups FETCH/PULL/DOWNLOAD
# together and PUSH/UPLOAD together - PROCESS is BUILD's own resource.
KIND_TO_RESOURCE = {
    "TRACK": "DOWNLOAD",
    "FETCH": "DOWNLOAD",
    "PULL": "DOWNLOAD",
    "BUILD": "PROCESS",
    "PUSH": "UPLOAD",
}


def chrome_events_to_bga_spans(events: Sequence[dict]) -> Tuple[List[dict], List[str]]:
    """Convert a list of Chrome Trace Event dicts into a list of trace/v9
    span dicts.

    Returns (spans, dropped) - dropped lists a short reason string for
    each bst-builder event pair that couldn't be converted (e.g. an
    unrecognized action word like "main", BuildStream's own top-level
    pseudo-activity bracket, which is not a real element task and has no
    TaskKind equivalent - not an error, just not span-worthy). Callers
    should look at dropped_names explicitly rather than silently ignore
    it, per this repo's established convention
    (tests/fixtures/synthetic_multi_subproject/adapter.py).
    """
    open_stack = defaultdict(list)  # (pid, tid) -> list of open B events
    pairs = []  # (begin_event, end_event)
    dropped: List[str] = []

    for ev in events:
        if ev.get("cat") != "bst-builder" or ev.get("ph") not in ("B", "E"):
            continue
        key = (ev.get("pid"), ev.get("tid"))

        if ev["ph"] == "B":
            open_stack[key].append(ev)
            continue

        stack = open_stack.get(key)
        if not stack:
            continue  # unmatched End with no Begin - shouldn't happen, ignore defensively
        begin_ev = stack.pop()
        pairs.append((begin_ev, ev))

    # Assign attempt numbers (Part 5.2) by chronological order among
    # occurrences sharing the same (element, kind) - the log itself has no
    # explicit attempt counter; a real re-invocation (e.g. a CI retry) is
    # only observable as the same (element, kind) recurring, so ordinal
    # position is the only real signal available. Matches the same
    # "chronological occurrence count" assumption bga/utilisation/detection.py's
    # compute_retry_tasks already relies on downstream.
    pairs.sort(key=lambda p: p[0].get("ts", 0))
    attempt_counter: dict = defaultdict(int)

    spans = []
    for begin_ev, end_ev in pairs:
        args = begin_ev.get("args") or {}
        action = args.get("action")
        element = args.get("element")
        kind = ACTION_TO_KIND.get(action)

        if kind is None or not element:
            dropped.append(
                f"{begin_ev.get('name', '<unnamed>')} (action={action!r}) - "
                f"unrecognized action, not a real element task"
            )
            continue

        attempt = attempt_counter[(element, kind)]
        attempt_counter[(element, kind)] += 1

        start_ts = begin_ev["ts"]
        end_ts = end_ev["ts"]
        resource = KIND_TO_RESOURCE[kind]

        span = {
            "task_key": f"{element}|{kind}|{kind}|{attempt}",
            "ts_us": int(start_ts),
            "dur_us": int(end_ts) - int(start_ts),
            "resources": [resource],
            "primary_resource": resource,
        }
        # UX-62: the task's own terminal status, which BuildStream states
        # and which every capture until now discarded at the span level.
        # `UX-54` recorded failure at the *run* level, which was the right
        # scope for the hazard it fixed (a broken build passing a CI
        # gate) but leaves two things unanswerable: which of an element's
        # attempts failed, and whether a span's duration was useful work
        # or work thrown away. Additive and optional - omitted rather
        # than defaulted when the log did not say, since "not recorded"
        # and "SUCCESS" are different claims.
        status = end_ev.get("args", {}).get("Status")
        if status:
            span["status"] = status
        spans.append(span)

    spans.sort(key=lambda s: (s["ts_us"], s["task_key"]))
    return spans, dropped


def failed_elements(events: Sequence[dict]) -> List[str]:
    """Elements whose task ended in `FAILURE` (UX-54).

    BuildStream's own log states each task's terminal status, and
    `bst_log_to_chrome_trace.py` already carries it through as the End
    event's `args.Status`. Nothing downstream read it, so a build in
    which every attempted element *failed* reached `bga` as ordinary
    work and scored 1.00 - measured on a real `freedesktop-sdk` capture
    whose four BUILD spans were four failed builds.

    Deliberately element names rather than task keys: the question the
    report has to answer is "did this build succeed", and the per-element
    detail is what makes the answer actionable. A retried element that
    fails once and succeeds later still appears here, which is the safe
    direction - it prompts a look rather than hiding one.
    """
    failed = set()
    for ev in events:
        if ev.get("cat") != "bst-builder" or ev.get("ph") != "E":
            continue
        args = ev.get("args") or {}
        if args.get("Status") == "FAILURE" and args.get("element"):
            failed.add(args["element"].strip())
    return sorted(failed)


def invocation_wall_clock(events: Sequence[dict]):
    """Earliest bst-invocation B timestamp and latest bst-invocation E
    timestamp, or (None, None) if no bst-invocation events are present -
    the same derivation tests/fixtures/synthetic_multi_subproject/generate_fixture.py
    already uses for its own synthetic run_context's wall_clock, reused
    here (via tools/bst_run_context.py, P4-09) for real runs.
    """
    begins = [e["ts"] for e in events if e.get("cat") == "bst-invocation" and e.get("ph") == "B"]
    ends = [e["ts"] for e in events if e.get("cat") == "bst-invocation" and e.get("ph") == "E"]
    if not begins or not ends:
        return None, None
    return min(begins), max(ends)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Chrome Trace Event JSON into trace/v9 JSON."
    )
    parser.add_argument("chrome_trace_json", help="Path to a Chrome Trace JSON file "
                         "(from tools/bst_log_to_chrome_trace.py).")
    parser.add_argument("output_json", help="Path to write the trace/v9 JSON to.")
    args = parser.parse_args()

    with open(args.chrome_trace_json, "r", encoding="utf-8") as f:
        events = json.load(f)

    spans, dropped = chrome_events_to_bga_spans(events)
    trace = {"spans": spans, "phases": []}

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2)

    print(f"Wrote trace.json with {len(spans)} span(s) to {args.output_json}")
    if dropped:
        print(f"Note: {len(dropped)} event(s) dropped:")
        for reason in dropped:
            print(f"  - {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
