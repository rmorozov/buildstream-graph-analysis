"""Ties the synthetic project model to the real log converter and produces
bga-ready fixture files.

Pipeline (every step is the real thing, nothing stubbed):
  build_model.simulate_schedule()   -> deterministic task timings
  build_model.generate_wrapper_log() -> a BuildStream CI wrapper log, byte-for-byte
  tools.bst_log_to_chrome_trace.WrapperTraceConverter -> Chrome Trace JSON (the
      user-supplied, unmodified converter - see tools/bst_log_to_chrome_trace.py)
  adapter.chrome_events_to_bga_spans() -> trace/v9 spans
  build_model.build_graph_dict()    -> graph/v9

Run this file directly to (re)write the checked-in copies under this
directory (wrapper.log, chrome_trace.json, run-context.json, graph.json,
trace.json) after changing the model in build_model.py. The test suite
(tests/test_synthetic_multi_subproject.py) regenerates everything fresh
into a tmp dir on every run and diffs it against these checked-in copies,
so drift between the model and the checked-in fixture fails loudly instead
of silently.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent
REPO_ROOT = FIXTURE_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.fixtures.synthetic_multi_subproject import (
    adapter,
    build_model,
)
from tools.bst_log_to_chrome_trace import WrapperTraceConverter

BASE_DT = datetime(2026, 8, 13, 9, 0, 0)


def build_fixture():
    """Run the full pipeline and return the artifacts as in-memory objects:
    (wrapper_log_text, chrome_events, run_context, graph, trace, dropped_names)
    """
    schedule = build_model.simulate_schedule()
    wrapper_log_text = build_model.generate_wrapper_log(schedule, BASE_DT)

    converter = WrapperTraceConverter()
    for line in wrapper_log_text.splitlines():
        converter.process_line(line)
    converter.end_current_command(converter.last_known_ts)
    chrome_events = json.loads(converter.get_json())

    spans, dropped_names = adapter.chrome_events_to_bga_spans(chrome_events)

    invocation_start = min(
        e["ts"] for e in chrome_events if e.get("cat") == "bst-invocation" and e.get("ph") == "B"
    )
    invocation_end = max(
        e["ts"] for e in chrome_events if e.get("cat") == "bst-invocation" and e.get("ph") == "E"
    )

    run_context = {
        "trace_epsilon_us": 50000,
        "wall_clock": {"start_us": invocation_start, "end_us": invocation_end},
        "host": "ci-runner-synthetic-01",
        "resource_capacities": dict(build_model.CAPACITIES),
        "max_jobs": build_model.MAX_JOBS,
        # Declares as many effective CPUs as the model's own PROCESS
        # capacity - without this, CPU reconciliation (Part 33.3) falls
        # back to the default effective_cpus=1.0 and reports a spurious
        # >2% reconciliation error against this fixture's real (4-way
        # concurrent) CPU usage, same class of gap fixed in
        # tests/fixtures/topologies.py (P3-01) and
        # tests/fixtures/golden/mixed_task_kinds/ (P3-08).
        "cpu_accounting": {"effective_cpus": build_model.CAPACITIES["PROCESS"]},
        # Consistent run_identity across all three files (P1-37) - full
        # provenance, matching a real extraction's identity guarantee.
        "run_identity": {"manifest_hash": "synthetic-multi-subproject-manifest-hash"},
    }
    graph = build_model.build_graph_dict()
    graph["run_identity_hash"] = "synthetic-multi-subproject-manifest-hash"
    trace = {"spans": spans, "phases": [], "run_identity_hash": "synthetic-multi-subproject-manifest-hash"}

    return wrapper_log_text, chrome_events, run_context, graph, trace, dropped_names


def write_fixture(out_dir: Path):
    wrapper_log_text, chrome_events, run_context, graph, trace, dropped_names = build_fixture()

    # Named wrapper_log.txt rather than wrapper.log - the repo's .gitignore
    # excludes *.log (real runtime logs), but this is checked-in fixture data.
    (out_dir / "wrapper_log.txt").write_text(wrapper_log_text)
    (out_dir / "chrome_trace.json").write_text(json.dumps(chrome_events, indent=2))
    (out_dir / "run-context.json").write_text(json.dumps(run_context, indent=2))
    (out_dir / "graph.json").write_text(json.dumps(graph, indent=2))
    (out_dir / "trace.json").write_text(json.dumps(trace, indent=2))

    return dropped_names


if __name__ == "__main__":
    dropped = write_fixture(FIXTURE_DIR)
    print(f"Wrote fixture files to {FIXTURE_DIR}")
    if dropped:
        print(f"Note: {len(dropped)} builder event(s) dropped by the adapter: {dropped}")
