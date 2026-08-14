#!/usr/bin/env python3
"""Convert a BuildStream log into Chrome Trace Event JSON.

Supports two input shapes, selected by `--format` (default `auto`,
detected per line):
  wrapped - a CI wrapper's log output (one bracketed prefix per line:
      `[tag][UTC timestamp] LEVEL: message`) wrapping BuildStream's own
      log lines. The wrapper's own UTC timestamp is the absolute time
      anchor; BuildStream's own elapsed-time prefix is not used.
  raw - a BuildStream log with no wrapper at all - BuildStream's own
      `[elapsed][hash][ action:element] STATUS message` lines directly.
      BuildStream's own log has no absolute time anchor (its `[HH:MM:SS]`
      prefix is elapsed time since the invocation started, not wall
      clock) - `--start-time` supplies one, defaulting to the input
      file's mtime.

Emits a Chrome Trace Event array (chrome://tracing / ui.perfetto.dev
compatible) with one swimlane per distinct BuildStream task hash.

Used by tests/fixtures/synthetic_multi_subproject/ as the real, unmodified
conversion path (wrapped mode) from a BuildStream run log to the trace
data bga ingests - see tests/test_synthetic_multi_subproject.py for the
integration. tools/chrome_trace_to_bga_trace.py converts this tool's
Chrome Trace output the rest of the way into trace/v9 (see
docs/ingestion-pipeline.md).
"""
import re
import json
import argparse
import os
from datetime import datetime, timezone

# Regex to match your EXACT wrapper prefix and extract UTC time + the raw message
PREFIX_RE = re.compile(r"^\[.*?\]\s*\[(.*?)\]\s*[A-Z]+:\s*(.*)$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Regex for specific wrapper events
EXEC_CMD_RE = re.compile(r"^Executing command:\s+(.*)$")
RETURN_CODE_RE = re.compile(r"^Return code:\s+(\d+)$")

# Regex for BuildStream's detailed log format (fixed for junctions and trailing spaces)
# [00:00:00][a59d6897][   build:my_package.bst] SUCCESS Staging dependencies at: /
#
# The elapsed-time bracket is captured (group 1) - unused by wrapped-mode
# processing (which anchors on the wrapper's own UTC timestamp instead)
# but required by raw mode, which has no other time source. `FAILURE` was
# added to the status alternation after a real failing build (BuildStream
# 2.7.0) showed the actual status word is "FAILURE", not "FAIL" - the
# original list never matched a real build failure at all, in either
# mode; `FAIL` is kept for tolerance in case another version/context uses
# it, but was never observed for real (see docs/ingestion-pipeline.md).
BST_LOG_RE = re.compile(
    r"\[([^\]]*)\]\[([^\]]+)\]\[\s*(\w+):([^\]]+)\]\s+"
    r"(START|SUCCESS|FAILURE|FAIL|CACHED|SKIPPED|SKIP)\s+(.*)"
)
BST_MAX_BUILD_RE = re.compile(r"Maximum Build Tasks:\s+(\d+)")
BST_MAX_FETCH_RE = re.compile(r"Maximum Fetch Tasks:\s+(\d+)")
BST_MAX_PUSH_RE = re.compile(r"Maximum Push Tasks:\s+(\d+)")

# BuildStream's own summary header prints the real, resolved target list
# unconditionally (e.g. "Targets:       base.bst, base2.bst") - present in
# both wrapped and raw logs since it comes from BuildStream itself, not
# the wrapper. This is a more reliable target-derivation source than
# parsing a wrapper's own shell command line (EXEC_CMD_RE), which only
# exists in wrapped logs and requires shell-quoting-aware parsing; see
# tools/bst_extract_run.py (P4-10), which uses this.
TARGETS_RE = re.compile(r"^\s*Targets:\s+(.*)$")

# BuildStream's own elapsed-time prefix: HH:MM:SS optionally followed by
# .ffffff (only shown with --verbose's microsecond mode), or the literal
# "--:--:--" (elapsed not yet known - shown for the very first event(s)
# before BuildStream's per-tick clock has advanced). Confirmed against a
# real BuildStream 2.7.0 build (see docs/ingestion-pipeline.md) - never
# observed a nonzero elapsed value in short test builds, but the format is
# also documented directly in BuildStream's own _frontend/widget.py
# (render_time).
ELAPSED_RE = re.compile(r"^(?:(\d\d):(\d\d):(\d\d)(?:\.(\d{6}))?|--:--:--(?:\.------)?)$")

# BuildStream's own bundled scheduler defaults (buildstream/data/userconfig.yaml,
# confirmed against a real BuildStream 2.7.0 install) - used only as a last
# resort when a log has no "Maximum {Fetch,Build,Push} Tasks:" header line
# to read the real, already-resolved values from (see get_scheduler_config).
DEFAULT_FETCHERS = 10
DEFAULT_BUILDERS = 4
DEFAULT_PUSHERS = 4


def parse_elapsed_to_seconds(elapsed_str):
    """Parse a BuildStream elapsed-time bracket's contents into seconds
    (float). Returns 0.0 for "--:--:--" (elapsed not yet known - the
    least-wrong interpretation, since that literally means "less than one
    visible tick has passed"), or None if the string doesn't match the
    known format at all.
    """
    m = ELAPSED_RE.match(elapsed_str.strip())
    if not m:
        return None
    if m.group(1) is None:
        return 0.0
    hours, minutes, seconds, micros = m.groups()
    total = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    if micros:
        total += int(micros) / 1_000_000
    return float(total)


class WrapperTraceConverter:
    def __init__(self, raw_start_time_us=None):
        """
        Args:
            raw_start_time_us: absolute epoch microseconds to anchor raw-mode
                (no-wrapper) elapsed timestamps against. Unused in wrapped
                mode, which anchors on each line's own wrapper UTC timestamp
                instead. Required (by process_line_raw) when processing raw
                lines.
        """
        self.trace_events = []
        self.last_known_ts = 0
        self.raw_start_time_us = raw_start_time_us

        # Wrapper state
        self.current_cmd = None
        self.current_cmd_start_ts = None
        self.is_bst = False

        # BuildStream state. Defaults match BuildStream's own bundled
        # scheduler defaults (see DEFAULT_* above) - overwritten if the log
        # contains the real "Maximum ... Tasks:" header lines, which report
        # the actual resolved values (including any CLI --builders/
        # --fetchers/--pushers override), not just the built-in default.
        self.bst_builders = DEFAULT_BUILDERS
        self.bst_fetchers = DEFAULT_FETCHERS
        self.bst_pushers = DEFAULT_PUSHERS
        self.targets = None  # from "Targets:" header, comma-separated string as seen
        self.hash_to_tid = {}  # Maps BST task hash (e.g. a59d6897) to a stable thread ID
        self.next_tid = 100
        # task_hash -> {"tid": int, "element": str, "phase": str, "action": str, "depth": int}
        # "depth" tracks nested START/terminal-status pairs sharing the same
        # (hash, action) - BuildStream emits an outer START/terminal bracket
        # per real task plus one or more *nested* START/terminal pairs for
        # internal sub-phases (e.g. "Staging sources", "Caching artifact"),
        # all under the identical hash+action key (confirmed against a real
        # build - see docs/ingestion-pipeline.md). Only the depth 0->1 START
        # opens a trace span and only the matching depth 1->0 terminal
        # closes it; without this, every nested sub-phase would be
        # mistaken for a new phase and force-close/reopen a spurious span,
        # producing several short spurious spans per real task instead of
        # one correct one. The synthetic fixture never nests (one START per
        # task), so this is a no-op there - verified byte-identical.
        self.active_tasks = {}

        # BuildStream also logs a family of top-level, non-element-scoped
        # "main:core activity" phases (Loading elements, Resolving
        # elements, Initializing remote caches, Query cache), all wrapped
        # by an outer "Build" bracket, before/around any real per-element
        # FETCH/BUILD/PULL/PUSH work. These are real work with a real
        # elapsed cost - confirmed material on a real ~2000-element
        # fully-cached rebuild (P4-14) - but chrome_trace_to_bga_trace.py
        # already, deliberately, drops action="main" events as "not a
        # real element task" since they have no per-element TaskKind
        # equivalent. Tracked here as a small, separate side list (never
        # fed into active_tasks/trace_events - the general per-hash depth
        # collapsing above is for genuinely nested sub-phases of one real
        # task, not this) so a consumer can surface each phase's own
        # aggregate elapsed time as a single number - not a per-element
        # breakdown, since that's not what BuildStream's own log
        # provides. These phases are confirmed strictly sequential, never
        # overlapping each other (only "Build" itself wraps them), so a
        # simple stack suffices. "Build" itself is excluded from the
        # recorded list - it spans the entire invocation and is redundant
        # with the horizon bga already computes elsewhere.
        self.pipeline_overhead = []
        self._main_activity_stack = []

    def get_scheduler_config(self):
        """Real (or defaulted) scheduler concurrency limits as observed in
        the log - see DEFAULT_* module constants for the fallback values
        and their source. Returned as a dict so tools/bst_run_context.py
        (P4-09) can consume it directly as run-context/v9's
        `resource_capacities`/`max_jobs` fields (PROCESS=builders,
        DOWNLOAD=fetchers, UPLOAD=pushers, max_jobs=builders - confirmed
        against real BuildStream: `--builders` is "Maximum simultaneous
        build tasks", the concurrency limit that actually gates dispatch;
        `--max-jobs` is a different, unrelated concept - parallelism
        *within* a single build task - and is not what run-context/v9's
        `max_jobs` field means).
        """
        return {
            "builders": self.bst_builders,
            "fetchers": self.bst_fetchers,
            "pushers": self.bst_pushers,
        }

    def parse_timestamp(self, ts_str):
        """Parses '2026-07-20 23:09:12,331' into epoch microseconds."""
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S,%f")
            return int(dt.timestamp() * 1_000_000)
        except ValueError:
            return None

    def get_tid_for_hash(self, hash_val):
        """Assigns a distinct swimlane (tid) for each BST task hash."""
        if hash_val not in self.hash_to_tid:
            self.hash_to_tid[hash_val] = self.next_tid
            self.next_tid += 1
        return self.hash_to_tid[hash_val]

    def end_current_command(self, end_ts, return_code=None):
        if not self.current_cmd:
            return

        event_args = {"Return Code": return_code} if return_code is not None else {}
        if return_code and return_code != "0":
            event_args["Error"] = True

        self.trace_events.append(
            {
                "name": self.current_cmd[:120]
                + ("..." if len(self.current_cmd) > 120 else ""),
                "cat": "bst-invocation" if self.is_bst else "wrapper",
                "ph": "E",
                "ts": end_ts,
                "pid": 1,
                "tid": 1,
                "args": event_args,
            }
        )

        if self.is_bst:
            # Force close any lingering builder tasks when the bst command ends
            for h, task in list(self.active_tasks.items()):
                self.trace_events.append(
                    {
                        "name": f"{task['element']} [{task['phase']}]",
                        "cat": "bst-builder",
                        "ph": "E",
                        "ts": end_ts,
                        "pid": 1,
                        "tid": task["tid"],
                    }
                )
            self.active_tasks.clear()

        self.current_cmd = None
        self.is_bst = False

    def _open_bst_invocation(self, ts, label="bst (raw log)"):
        """Synthesize the bst-invocation B event raw mode has no wrapper
        'Executing command:' line to trigger - the whole raw log is one
        continuous bst invocation by definition. Kept as its own method
        so wrapped mode's real EXEC_CMD_RE-triggered path (which carries
        the real command text) is untouched.
        """
        self.current_cmd = label
        self.is_bst = True
        self.trace_events.append(
            {
                "name": label,
                "cat": "bst-invocation",
                "ph": "B",
                "ts": ts,
                "pid": 1,
                "tid": 1,
                "args": {"Full Command": label},
            }
        )

    def _check_header_lines(self, text):
        """Check a line of BuildStream's own summary-header output
        (`Maximum {Fetch,Build,Push} Tasks:`, `Targets:`) - these are
        standalone lines (no `[hash][action:element] STATUS` bracket
        structure at all, confirmed against a real build), not per-task
        log lines, so they never reach handle_bst_event's BST_LOG_RE
        matching. Called against the wrapper-stripped message in wrapped
        mode, and the raw line directly in raw mode - both are real
        places these lines can appear (a CI wrapper wraps *every* line of
        bst's stdout, header included).
        """
        max_build_match = BST_MAX_BUILD_RE.search(text)
        if max_build_match:
            self.bst_builders = int(max_build_match.group(1))
        max_fetch_match = BST_MAX_FETCH_RE.search(text)
        if max_fetch_match:
            self.bst_fetchers = int(max_fetch_match.group(1))
        max_push_match = BST_MAX_PUSH_RE.search(text)
        if max_push_match:
            self.bst_pushers = int(max_push_match.group(1))
        targets_match = TARGETS_RE.search(text)
        if targets_match:
            self.targets = targets_match.group(1).strip()

    def handle_bst_event(self, ts, hash_val, action, element, status, msg):
        # Clean up any accidental trailing whitespace from regex extraction
        action = action.strip()
        element = element.strip()

        if action == "main":
            self._handle_main_activity(ts, status, msg)
            return

        if status == "START":
            if hash_val in self.active_tasks:
                # Nested sub-phase of an already-open task (same hash+action) -
                # just track depth, don't touch the open span.
                self.active_tasks[hash_val]["depth"] += 1
                return

            phase = msg.strip()
            tid = self.get_tid_for_hash(hash_val)
            self.active_tasks[hash_val] = {
                "tid": tid,
                "element": element,
                "phase": phase,
                "action": action,
                "depth": 1,
            }
            self.trace_events.append(
                {
                    "name": f"{element} [{phase}]",
                    "cat": "bst-builder",
                    "ph": "B",
                    "ts": ts,
                    "pid": 1,
                    "tid": tid,
                    "args": {"action": action, "element": element},
                }
            )
        else:  # SUCCESS, FAILURE, etc.
            task = self.active_tasks.get(hash_val)
            if task is None:
                return
            task["depth"] -= 1
            if task["depth"] > 0:
                # Closes a nested sub-phase only - the outer span stays open.
                return
            self.active_tasks.pop(hash_val)
            self.trace_events.append(
                {
                    "name": f"{task['element']} [{task['phase']}]",
                    "cat": "bst-builder",
                    "ph": "E",
                    "ts": ts,
                    "pid": 1,
                    "tid": task["tid"],
                    "args": {
                        "Status": status,
                        "Message": msg,
                        "action": task["action"],
                        "element": task["element"],
                    },
                }
            )

    def _handle_main_activity(self, ts, status, msg):
        """Track BuildStream's top-level "main:core activity" phases
        (see the `pipeline_overhead`/`_main_activity_stack` comment in
        __init__) - a small, separate stack, deliberately not routed
        through active_tasks/trace_events at all.
        """
        phase = msg.strip()
        if status == "START":
            self._main_activity_stack.append({"phase": phase, "start_ts": ts})
            return
        if not self._main_activity_stack:
            # Unmatched terminal status with nothing open - shouldn't
            # happen in a real log, ignore defensively.
            return
        frame = self._main_activity_stack.pop()
        if frame["phase"] == "Build":
            # The outermost wrapper spans the entire invocation - redundant
            # with the horizon bga already computes elsewhere.
            return
        self.pipeline_overhead.append({
            "phase": frame["phase"],
            "elapsed_us": ts - frame["start_ts"],
        })

    def process_line(self, line):
        """Process one line, auto-detecting wrapped vs. raw format per
        line (matches the module docstring's `--format auto` default)."""
        line = ANSI_RE.sub("", line)

        match = PREFIX_RE.search(line)
        if match:
            self._process_wrapped_line(*match.groups())
            return

        self._process_raw_line(line)

    def process_line_wrapped(self, line):
        """Process one line, requiring the wrapper prefix (`--format
        wrapped`) - does not fall back to raw parsing."""
        line = ANSI_RE.sub("", line)
        match = PREFIX_RE.search(line)
        if not match:
            return
        self._process_wrapped_line(*match.groups())

    def process_line_raw(self, line):
        """Process one raw (unwrapped) BuildStream log line (`--format
        raw`) - does not attempt wrapper-prefix stripping."""
        line = ANSI_RE.sub("", line)
        self._process_raw_line(line)

    def _process_wrapped_line(self, utc_time_str, raw_msg):
        ts = self.parse_timestamp(utc_time_str)
        if ts is None:
            ts = self.last_known_ts
        else:
            self.last_known_ts = ts

        msg = raw_msg.strip()

        self._check_header_lines(msg)

        exec_match = EXEC_CMD_RE.search(msg)
        if exec_match:
            self.end_current_command(ts)

            self.current_cmd = exec_match.group(1)
            self.current_cmd_start_ts = ts

            self.is_bst = " bst " in self.current_cmd or self.current_cmd.startswith(
                "bst "
            )

            self.trace_events.append(
                {
                    "name": self.current_cmd[:120]
                    + ("..." if len(self.current_cmd) > 120 else ""),
                    "cat": "bst-invocation" if self.is_bst else "wrapper",
                    "ph": "B",
                    "ts": ts,
                    "pid": 1,
                    "tid": 1,
                    "args": {"Full Command": self.current_cmd},
                }
            )
            return

        ret_match = RETURN_CODE_RE.search(msg)
        if ret_match:
            self.end_current_command(ts, ret_match.group(1))
            return

        if self.is_bst:
            bst_match = BST_LOG_RE.search(msg)
            if bst_match:
                _elapsed, h, action, element, status, b_msg = bst_match.groups()
                self.handle_bst_event(ts, h, action, element, status, b_msg)
                return

    def _process_raw_line(self, line):
        """No wrapper prefix at all - try BST_LOG_RE directly against the
        raw line. The whole raw log is treated as one continuous bst
        invocation (there's no wrapper "Executing command:" line to
        trigger is_bst - see _open_bst_invocation). BuildStream's own
        elapsed-time prefix is the only time source, converted to
        absolute microseconds via self.raw_start_time_us.
        """
        self._check_header_lines(line)

        bst_match = BST_LOG_RE.search(line)
        if not bst_match:
            return

        elapsed_str, h, action, element, status, b_msg = bst_match.groups()
        elapsed_s = parse_elapsed_to_seconds(elapsed_str)
        if elapsed_s is None:
            return
        if self.raw_start_time_us is None:
            raise ValueError(
                "raw_start_time_us is required to process raw-format lines"
            )
        ts = self.raw_start_time_us + int(elapsed_s * 1_000_000)
        self.last_known_ts = ts

        if not self.is_bst:
            self._open_bst_invocation(ts)

        self.handle_bst_event(ts, h, action, element, status, b_msg)

    def get_json(self):
        meta_events = [
            {
                "name": "process_name",
                "ph": "M",
                "pid": 1,
                "args": {"name": "Build System Wrapper"},
            },
            {
                "name": "thread_name",
                "ph": "M",
                "pid": 1,
                "tid": 1,
                "args": {"name": "Sequential Commands"},
            },
            {
                "name": "thread_sort_index",
                "ph": "M",
                "pid": 1,
                "tid": 1,
                "args": {"sort_index": 0},
            },
        ]

        # Add metadata for all the distinct builder threads we discovered
        for h, tid in self.hash_to_tid.items():
            meta_events.append(
                {
                    "name": "thread_name",
                    "ph": "M",
                    "pid": 1,
                    "tid": tid,
                    "args": {"name": f"Builder {tid - 99} ({h[:8]})"},
                }
            )
            meta_events.append(
                {
                    "name": "thread_sort_index",
                    "ph": "M",
                    "pid": 1,
                    "tid": tid,
                    "args": {"sort_index": tid},
                }
            )

        return json.dumps(meta_events + self.trace_events, indent=2)


def _resolve_start_time_us(start_time_arg, input_log_path):
    """--start-time accepts an ISO-8601 timestamp; defaults to the input
    file's mtime (the least-wrong anchor available when the user doesn't
    know or care about absolute time - raw-log timestamps only need
    internal consistency, Part 3.1, not a particular real-world epoch)."""
    if start_time_arg:
        dt = datetime.fromisoformat(start_time_arg)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1_000_000)
    mtime = os.path.getmtime(input_log_path)
    return int(mtime * 1_000_000)


def main():
    parser = argparse.ArgumentParser(
        description="Convert a BuildStream log (wrapped or raw) to Chrome Trace Event JSON."
    )
    parser.add_argument("input_log", help="Path to the log file")
    parser.add_argument("output_json", help="Path to save the output trace.json file")
    parser.add_argument(
        "--format",
        choices=("auto", "wrapped", "raw"),
        default="auto",
        help="Input log format: 'wrapped' (CI wrapper prefix required), "
        "'raw' (BuildStream's own log lines only, no wrapper), or "
        "'auto' (try wrapped first, fall back to raw, per line - default)",
    )
    parser.add_argument(
        "--start-time",
        default=None,
        help="ISO-8601 timestamp to anchor raw-format elapsed timestamps "
        "against (only meaningful with --format raw or auto's raw "
        "fallback). Defaults to the input file's mtime.",
    )
    args = parser.parse_args()

    try:
        start_time_us = _resolve_start_time_us(args.start_time, args.input_log)
    except FileNotFoundError:
        print(f"Error: Could not find input file '{args.input_log}'")
        return

    converter = WrapperTraceConverter(raw_start_time_us=start_time_us)

    try:
        with open(args.input_log, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if args.format == "wrapped":
                    converter.process_line_wrapped(line)
                elif args.format == "raw":
                    converter.process_line_raw(line)
                else:
                    converter.process_line(line)
        # FIX: Use last_known_ts instead of 0 to prevent broken trace blocks at EOF
        converter.end_current_command(converter.last_known_ts)
    except FileNotFoundError:
        print(f"Error: Could not find input file '{args.input_log}'")
        return

    with open(args.output_json, "w") as f:
        f.write(converter.get_json())

    print(
        f"Successfully generated trace! Open {args.output_json} in chrome://tracing or ui.perfetto.dev"
    )


if __name__ == "__main__":
    main()
