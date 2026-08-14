#!/usr/bin/env python3
"""Convert real `bst show` output into graph/v9 JSON (Part 32.2) for bga.

Calls `bst show --deps all --format ...` against a live BuildStream
project and emits `{"elements": [...], "dependencies": [...]}` -
graph.json's exact shape, ready to sit alongside a trace.json produced
by bst_log_to_chrome_trace.py (or its wrapped-log converter) for the
same invocation.

Design decisions (settled empirically against a real `bst` 2.7.0
install - see docs/ingestion-pipeline.md for the full record and the
reasoning behind each):

- Targets are passed explicitly by the caller (the actual elements a
  real `bst build`/`bst show` invocation named), not assumed from a
  project convention like "all.bst" - so `requested_target` always
  reflects what was really invoked, not what the extraction tool
  guessed. Get the real target list from the same source the trace
  came from (e.g. a wrapper log's "Executing command: ... bst build
  <targets>" line) rather than re-deriving it here.
- `%{build-deps}`/`%{runtime-deps}` return each element's own DIRECT
  dependencies (not a transitive closure) as a multi-line "- name"
  list - confirmed by testing against a real multi-dependency element,
  which showed this list can contain embedded newlines. A naive
  line-by-line stdout parser silently corrupts multi-dependency
  records for exactly this reason - this tool instead delimits the
  whole record set with ASCII RS/US control characters via the
  --format string itself, and parses the full stdout blob, not lines.
- An element's cache_key (%{key}) can come back empty when its sources
  aren't consistent (unpinned/unresolvable refs) - this maps to
  cache_key: null, not a fabricated placeholder (same "no silent
  correction" philosophy the rest of bga's ingestion follows).
- A dependency declared as BuildStream's default type ("all" - both
  build and runtime) appears in *both* %{build-deps} and
  %{runtime-deps} for the same element. Since bga's graph/v9 schema
  models one dependency_type per edge (Part 32.2) and nothing
  downstream yet needs a genuine tri-state, an edge present in
  build-deps is always emitted as "build" (a strict superset of what
  "runtime" alone would constrain), even if it's also present in
  runtime-deps; only edges present in runtime-deps *and not* in
  build-deps are emitted as "runtime".
- Junction-qualified element names (`junction-name:element-name`)
  round-trip identically between `bst show`'s %{name} and a real `bst
  build`'s own log lines - confirmed empirically, so no special-casing
  is needed here for tools/bst_log_to_chrome_trace.py's element names
  to line up with this tool's graph.json uids.
- Each element's BuildStream plugin kind (%{kind}, Since: 2.6 - present
  in the real 2.7.0 install this was verified against) is captured as
  `element_kind` (e.g. "import", "manual", "junction", "autotools") -
  not part of graph/v9's spec-mandated minimal schema (Part 32.2's JSON
  example is illustrative, not exhaustive; `dependency_type` is an
  existing precedent for the same kind of additive extension). No
  analysis consumer reads it yet - see docs/tasks/P4-12 for planned
  kind-based heuristics (a junction or import element's own build work
  is structurally different from an autotools/cmake element's, a real
  signal worth exploring once there's a task scoping exactly how).

Out of scope here (see docs/ingestion-pipeline.md / P4-08's follow-on
tasks): run-context.json production (resource capacities, wall clock -
those come from the real invocation's own environment/config, not from
`bst show`), and wiring this together with the trace-side converter
into one convenience command.
"""
import argparse
import json
import subprocess
import sys
from typing import List, Sequence

RECORD_SEP = "\x1e"  # ASCII Record Separator - between elements
FIELD_SEP = "\x1f"  # ASCII Unit Separator - between fields of one element

_FORMAT = FIELD_SEP.join(
    ["%{name}", "%{key}", "%{kind}", "%{build-deps}", "%{runtime-deps}"]
) + RECORD_SEP


def _parse_dep_list(raw: str) -> List[str]:
    """Parse a %{build-deps}/%{runtime-deps} value: empty renders as the
    literal string "[]"; a non-empty list renders as one "- name" line
    per dependency, which can span multiple physical lines for a
    single element - never split on newlines to find field/record
    boundaries, only on RECORD_SEP/FIELD_SEP (see run_bst_show)."""
    raw = raw.strip()
    if not raw or raw == "[]":
        return []
    deps = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("- "):
            deps.append(line[2:].strip())
    return deps


def run_bst_show(
    project_dir: str,
    targets: Sequence[str],
    bst_bin: str = "bst",
) -> str:
    """Run `bst show --deps all` against project_dir for the given
    targets and return raw stdout. Progress/log output goes to bst's
    own stderr, never mixed into stdout - confirmed empirically, so
    stdout only ever contains --format output."""
    cmd = [bst_bin, "show", "--deps", "all", "--format", _FORMAT, *targets]
    proc = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"bst show failed (exit {proc.returncode}) for targets {list(targets)}: "
            f"{proc.stderr.strip()}"
        )
    return proc.stdout


def build_graph(stdout: str, targets: Sequence[str]) -> dict:
    """Parse run_bst_show's stdout into graph/v9's {"elements", "dependencies"} shape."""
    requested = set(targets)
    elements: List[dict] = []
    dependencies: List[dict] = []
    seen_uids = set()

    for record in stdout.split(RECORD_SEP):
        if not record.strip():
            continue
        fields = record.split(FIELD_SEP)
        if len(fields) != 5:
            # Defensive: a malformed/unexpected record (e.g. a future
            # bst version changing --format's output shape) should be
            # visible, not silently dropped or crash the whole run.
            print(f"warning: skipping malformed bst show record: {fields!r}", file=sys.stderr)
            continue

        name, key, kind, build_deps_raw, runtime_deps_raw = (f.strip() for f in fields)
        if not name or name in seen_uids:
            continue
        seen_uids.add(name)

        elements.append({
            "uid": name,
            "cache_key": key or None,
            "requested_target": name in requested,
            # BuildStream's own plugin kind (%{kind}, Since: 2.6 - confirmed
            # against a real BuildStream 2.7.0 install: e.g. "import",
            # "manual", "junction", "autotools"). Not part of graph/v9's
            # spec-mandated minimal schema (Part 32.2's JSON example is
            # illustrative, not exhaustive - dependency_type is an existing
            # precedent for the same kind of additive extension) - bga
            # doesn't act on it yet, see P4-12 for planned heuristics.
            "element_kind": kind or None,
        })

        build_deps = set(_parse_dep_list(build_deps_raw))
        runtime_deps = set(_parse_dep_list(runtime_deps_raw))
        for dep in sorted(build_deps):
            dependencies.append({"predecessor": dep, "successor": name, "dependency_type": "build"})
        for dep in sorted(runtime_deps - build_deps):
            dependencies.append({"predecessor": dep, "successor": name, "dependency_type": "runtime"})

    return {"elements": elements, "dependencies": dependencies}


def extract_graph(
    project_dir: str,
    targets: Sequence[str],
    bst_bin: str = "bst",
) -> dict:
    """Run bst show and parse its output in one call - the entry point
    other tools/tests should import, rather than reaching for
    run_bst_show/build_graph separately."""
    stdout = run_bst_show(project_dir, targets, bst_bin=bst_bin)
    return build_graph(stdout, targets)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert real `bst show` output into graph/v9 JSON for bga.",
    )
    parser.add_argument("project_dir", help="Path to the BuildStream project directory")
    parser.add_argument(
        "targets", nargs="+",
        help="Element(s) actually passed to the real bst build/show invocation "
             "being analyzed - these are marked requested_target: true",
    )
    parser.add_argument("output_json", help="Path to write graph.json to")
    parser.add_argument(
        "--bst-bin", default="bst",
        help="Path to the bst executable (default: bst, resolved via PATH)",
    )
    args = parser.parse_args()

    try:
        graph = extract_graph(args.project_dir, args.targets, bst_bin=args.bst_bin)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    with open(args.output_json, "w") as f:
        json.dump(graph, f, indent=2)

    print(
        f"Wrote graph.json with {len(graph['elements'])} elements, "
        f"{len(graph['dependencies'])} dependencies to {args.output_json}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
