"""Adapts tools/bst_log_to_chrome_trace.py output into bga's trace/v9 shape.

bga's own Chrome-trace ingestion (bga.ingest.loader.load_trace, the
'traceEvents' branch) only understands complete ('X') and phase ('P')
events. The real converter emits begin/end ('B'/'E') pairs instead, one
per BuildStream task, which load_trace currently has no handling for at
all - they would be silently ignored and the trace would come out empty.
This is a genuine format mismatch between the two tools, not a hypothetical
one; this adapter is the bridge until bga's loader grows native B/E
support (see docs/fix-progress-tracker.md for a tracked follow-up).

The converter's emitted event `name` is "<element> [<phase message>]" -
the BuildStream task-kind word (track/fetch/build) itself is discarded by
the converter (see WrapperTraceConverter.handle_bst_event), so the only
way to recover it here is via the phase message text, using the same
PHASE_MESSAGE mapping the fixture generator used to write the synthetic
log in the first place (build_model.MESSAGE_TO_KIND).
"""
import re

from tests.fixtures.synthetic_multi_subproject.build_model import MESSAGE_TO_KIND

_NAME_RE = re.compile(r"^(.*) \[(.*)\]$")

_KIND_TO_RESOURCE = {"TRACK": "DOWNLOAD", "FETCH": "DOWNLOAD", "BUILD": "PROCESS"}


def chrome_events_to_bga_spans(events):
    """Convert a list of Chrome Trace Event dicts (as emitted by
    WrapperTraceConverter.get_json(), already json.loads()'d) into a list
    of trace/v9 span dicts.

    Returns (spans, dropped_names) - dropped_names lists any bst-builder
    event whose name didn't parse as "<element> [<known phase message>]",
    e.g. because it was force-closed with a generic name, or because a
    phase message wasn't one bga's task-kind mapping recognizes. Callers
    should assert on dropped_names explicitly rather than silently ignore
    it - a growing drop list usually means the fixture and the adapter
    have drifted apart.
    """
    open_stack = {}  # (pid, tid) -> list of (name, ts)
    spans = []
    dropped_names = []

    for ev in events:
        if ev.get("cat") != "bst-builder" or ev.get("ph") not in ("B", "E"):
            continue
        key = (ev["pid"], ev["tid"])

        if ev["ph"] == "B":
            open_stack.setdefault(key, []).append((ev["name"], ev["ts"]))
            continue

        stack = open_stack.get(key)
        if not stack:
            continue  # unmatched End with no Begin - shouldn't happen, ignore defensively
        name, start_ts = stack.pop()
        end_ts = ev["ts"]

        m = _NAME_RE.match(name)
        if not m:
            dropped_names.append(name)
            continue
        element, message = m.group(1), m.group(2)
        kind = MESSAGE_TO_KIND.get(message)
        if kind is None:
            dropped_names.append(name)
            continue

        resource = _KIND_TO_RESOURCE[kind]
        spans.append({
            "task_key": f"{element}|{kind}|{kind}|0",
            "ts_us": int(start_ts),
            "dur_us": int(end_ts) - int(start_ts),
            "resources": [resource],
            "primary_resource": resource,
        })

    spans.sort(key=lambda s: (s["ts_us"], s["task_key"]))
    return spans, dropped_names
