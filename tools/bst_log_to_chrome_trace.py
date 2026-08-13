#!/usr/bin/env python3
"""Convert a BuildStream CI wrapper log into Chrome Trace Event JSON.

Parses a wrapper script's log output (one JSON-ish bracketed prefix per
line: `[tag][UTC timestamp] LEVEL: message`) wrapping BuildStream's own
`[elapsed][hash][ action:element] STATUS message` log lines, and emits a
Chrome Trace Event array (chrome://tracing / ui.perfetto.dev compatible)
with one swimlane per distinct BuildStream task hash.

Used by tests/fixtures/synthetic_multi_subproject/ as the real, unmodified
conversion path from a BuildStream run log to the trace data bga ingests -
see tests/test_synthetic_multi_subproject.py for the integration.
"""
import re
import json
import argparse
from datetime import datetime

# Regex to match your EXACT wrapper prefix and extract UTC time + the raw message
PREFIX_RE = re.compile(r"^\[.*?\]\s*\[(.*?)\]\s*[A-Z]+:\s*(.*)$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Regex for specific wrapper events
EXEC_CMD_RE = re.compile(r"^Executing command:\s+(.*)$")
RETURN_CODE_RE = re.compile(r"^Return code:\s+(\d+)$")

# Regex for BuildStream's detailed log format (fixed for junctions and trailing spaces)
# [00:00:00][a59d6897][   build:my_package.bst] SUCCESS Staging dependencies at: /
BST_LOG_RE = re.compile(
    r"\[[^\]]*\]\[([^\]]+)\]\[\s*(\w+):([^\]]+)\]\s+"
    r"(START|SUCCESS|FAIL|CACHED|SKIPPED|SKIP)\s+(.*)"
)
BST_MAX_BUILD_RE = re.compile(r"Maximum Build Tasks:\s+(\d+)")


class WrapperTraceConverter:
    def __init__(self):
        self.trace_events = []
        self.last_known_ts = 0

        # Wrapper state
        self.current_cmd = None
        self.current_cmd_start_ts = None
        self.is_bst = False

        # BuildStream state
        self.bst_max_jobs = 4
        self.hash_to_tid = {}  # Maps BST task hash (e.g. a59d6897) to a stable thread ID
        self.next_tid = 100
        self.active_tasks = {}  # task_hash -> {"tid": int, "element": str, "phase": str}

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

    def handle_bst_event(self, ts, hash_val, action, element, status, msg):
        # Clean up any accidental trailing whitespace from regex extraction
        action = action.strip()
        element = element.strip()

        if status == "START":
            phase = msg.strip()
            tid = self.get_tid_for_hash(hash_val)

            # If this builder was already doing a phase, implicitly close it before starting the new one
            if hash_val in self.active_tasks:
                task = self.active_tasks[hash_val]
                self.trace_events.append(
                    {
                        "name": f"{task['element']} [{task['phase']}]",
                        "cat": "bst-builder",
                        "ph": "E",
                        "ts": ts,
                        "pid": 1,
                        "tid": tid,
                    }
                )

            self.active_tasks[hash_val] = {
                "tid": tid,
                "element": element,
                "phase": phase,
            }
            self.trace_events.append(
                {
                    "name": f"{element} [{phase}]",
                    "cat": "bst-builder",
                    "ph": "B",
                    "ts": ts,
                    "pid": 1,
                    "tid": tid,
                }
            )
        else:  # SUCCESS, FAIL, etc.
            if hash_val in self.active_tasks:
                task = self.active_tasks.pop(hash_val)
                self.trace_events.append(
                    {
                        "name": f"{task['element']} [{task['phase']}]",
                        "cat": "bst-builder",
                        "ph": "E",
                        "ts": ts,
                        "pid": 1,
                        "tid": task["tid"],
                        "args": {"Status": status, "Message": msg},
                    }
                )

    def process_line(self, line):
        # 1. Remove ANSI color codes first
        line = ANSI_RE.sub("", line)

        # 2. Match the wrapper prefix and extract the actual message
        match = PREFIX_RE.search(line)
        if not match:
            return

        utc_time_str, raw_msg = match.groups()
        ts = self.parse_timestamp(utc_time_str)
        if ts is None:
            ts = self.last_known_ts
        else:
            self.last_known_ts = ts

        msg = raw_msg.strip()

        # 3. Check for config line defining max build tasks
        max_build_match = BST_MAX_BUILD_RE.search(msg)
        if max_build_match:
            self.bst_max_jobs = int(max_build_match.group(1))

        # 4. Check for Wrapper Command Execution
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

        # 5. Check for Wrapper Return Code
        ret_match = RETURN_CODE_RE.search(msg)
        if ret_match:
            self.end_current_command(ts, ret_match.group(1))
            return

        # 6. If inside a BST invocation, parse BST internal detailed logs
        if self.is_bst:
            bst_match = BST_LOG_RE.search(msg)
            if bst_match:
                h, action, element, status, b_msg = bst_match.groups()
                self.handle_bst_event(ts, h, action, element, status, b_msg)
                return

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


def main():
    parser = argparse.ArgumentParser(
        description="Convert wrapper log to Chrome Trace Event JSON."
    )
    parser.add_argument("input_log", help="Path to the wrapper script's log file")
    parser.add_argument("output_json", help="Path to save the output trace.json file")
    args = parser.parse_args()

    converter = WrapperTraceConverter()

    try:
        with open(args.input_log, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
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
