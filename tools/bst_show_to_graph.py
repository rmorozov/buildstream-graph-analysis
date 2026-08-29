#!/usr/bin/env python3
"""Convert real `bst show` output into graph/v9 JSON (Part 32.2) for bga.

Calls `bst show --deps all --format ...` against a live BuildStream
project and emits `{"elements": [...], "dependencies": [...]}` -
graph.json's exact shape, ready to sit alongside a trace.json produced
by bst_log_to_chrome_trace.py (or its wrapped-log converter) for the
same invocation.

Design decisions (settled empirically against a real `bst` 2.7.0
install - see docs/spec/ingestion-pipeline.md for the full record and the
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
  analysis consumer reads it yet - see docs/backlog/tasks/P4-12 for planned
  kind-based heuristics (a junction or import element's own build work
  is structurally different from an autotools/cmake element's, a real
  signal worth exploring once there's a task scoping exactly how).

Out of scope here (see docs/spec/ingestion-pipeline.md / P4-08's follow-on
tasks): run-context.json production (resource capacities, wall clock -
those come from the real invocation's own environment/config, not from
`bst show`), and wiring this together with the trace-side converter
into one convenience command.
"""
import argparse
import json
import subprocess
import tempfile
import time

from bga import progress
import sys
from typing import List, Optional, Sequence

RECORD_SEP = "\x1e"  # ASCII Record Separator - between elements
FIELD_SEP = "\x1f"  # ASCII Unit Separator - between fields of one element

_FORMAT = FIELD_SEP.join(
    ["%{name}", "%{key}", "%{kind}", "%{build-deps}", "%{runtime-deps}", "%{public}", "%{vars}"]
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


def _parse_yaml_mapping(raw: str) -> dict:
    """Parse one of `bst show`'s YAML-mapping format symbols
    (`%{vars}`, `%{public}`). Returns {} for anything unparseable rather
    than raising - a future bst version changing the shape must degrade
    to "unknown", not crash the extraction."""
    try:
        import yaml
    except ImportError as e:
        raise RuntimeError(
            "per-element max-jobs capture requires PyYAML "
            "(pip install -e '.[bst]', which now includes pyyaml)"
        ) from e
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _parse_notparallel(vars_raw: str) -> Optional[bool]:
    """UX-31: BuildStream's real per-element parallelism control, read
    from `%{vars}`.

    `variables: notparallel: True` on an element is what BuildStream and
    `buildstream-plugins` actually document for this ("Set this if the
    sources cannot handle parallelization", commented out in
    cmake.yaml/make.yaml/meson.yaml/autotools.yaml), and it is the only
    per-element parallelism control BuildStream 2.7.0 has - `max-jobs`
    itself is a protected, project-wide base variable that an element may
    not redefine.

    None (not False) when the element doesn't set it: "didn't say" and
    "said no" are different, and only the former should be silent.
    """
    value = _parse_yaml_mapping(vars_raw).get("notparallel")
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    # BuildStream renders variables as strings; anything non-empty and
    # not an explicit false-ish word counts as set, matching
    # `Element.get_variable("notparallel")`'s own truthiness use.
    return str(value).strip().lower() not in ("", "false", "0", "no")


def _parse_effective_max_jobs(vars_raw: str, public_raw: str) -> Optional[int]:
    """UX-31: the real, resolved `max-jobs` this element's own native
    build system was given, read from `%{vars}` - which is what
    `%{max-jobs}` expands to in the plugins' own
    `environment: JOBS: -j%{max-jobs}`, i.e. the number that really
    reaches `make`.

    This corrects `UX-22`'s capture route. That task concluded `%{vars}`
    "always reports the project-wide default, never a per-element
    override" and settled on `public: bst: max-jobs:` instead. Re-checked
    against a real BuildStream 2.7.0 build of
    `examples/06-macro-micro-optimization`, that is not so: an element
    carrying `notparallel: True` reports `max-jobs: 1` in its own
    `%{vars}` while every sibling reports `max-jobs: 4`, and the traced
    sandbox really did run `make -j1` for it and `make -j4` for them.
    (`UX-22`'s conclusion holds for what it actually tested - writing
    `variables: max-jobs:` directly on an element, which BuildStream
    rejects as a protected-variable redefinition. The `notparallel` path
    is a different one and it does reach `%{vars}`.)

    `public: bst: max-jobs:` is kept only as a fallback for run
    directories captured before this change: BuildStream itself never
    reads that key, so it cannot describe what a build really did, but
    dropping it outright would silently change what an existing
    `graph.json` means.
    """
    value = _parse_yaml_mapping(vars_raw).get("max-jobs")
    if value is not None:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            pass
    return _parse_max_jobs(public_raw)


def _parse_max_jobs(public_raw: str) -> Optional[int]:
    """Parse a %{public} value for a real per-element `max-jobs` override
    (UX-22 - a real BuildStream possibility: an element can be given
    more/less native build-system parallelism than the project default,
    e.g. a large single-synchronization-point element like an LLVM build
    given the full host core count).

    **Superseded by `_parse_effective_max_jobs` (UX-31) - kept only as
    its fallback for run directories captured before that change.**
    BuildStream never reads a `max-jobs` key out of `public:`, so this
    value cannot describe what a build actually did; `%{vars}` can, and
    now does. `variables: max-jobs:` on an element really is rejected as
    a protected-variable redefinition (UX-22 confirmed that, and it still
    holds), but UX-22's other conclusion - that `%{vars}` only ever shows
    the project-wide default - was re-checked against a real
    BuildStream 2.7.0 build and found not to hold for the `notparallel`
    path. See `_parse_effective_max_jobs`'s docstring for the real
    evidence.
    """
    try:
        import yaml
    except ImportError as e:
        raise RuntimeError(
            "per-element max-jobs capture requires PyYAML "
            "(pip install -e '.[bst]', which now includes pyyaml)"
        ) from e
    try:
        data = yaml.safe_load(public_raw) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    bst_block = data.get("bst")
    if not isinstance(bst_block, dict):
        return None
    value = bst_block.get("max-jobs")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def run_bst_show(
    project_dir: str,
    targets: Sequence[str],
    bst_bin: str = "bst",
    bst_options: Optional[Sequence[str]] = None,
) -> str:
    """Run `bst show --deps all` against project_dir for the given
    targets and return raw stdout. Progress/log output goes to bst's
    own stderr, never mixed into stdout - confirmed empirically, so
    stdout only ever contains --format output."""
    # `UX-377`: the build's own scheduler options, replayed. `max-jobs`
    # is a *top-level* `bst` option and it reaches `%{vars}`, so a
    # `bst show` run without it resolves whatever the config says and
    # reports that as the element's `max_jobs` - which is not what the
    # build ran at. Measured: a cold capture under `bst --max-jobs 2
    # build` ran `make -j2` in five sandboxes and its graph said 4.
    cmd = [bst_bin, *(bst_options or []),
           "show", "--deps", "all", "--format", _FORMAT, *targets]
    # UX-183: on a large project this is minutes inside one phase line,
    # and there is nothing to count - `bst` is a subprocess and its
    # stdout is the payload, not a progress stream. Elapsed seconds are
    # the honest signal: "still running, 40s" beats a cursor that has
    # not moved.
    #
    # Both streams go to temporary files rather than pipes. It is what
    # makes the wait pollable at all, and it removes the pipe-buffer
    # deadlock that a project with thousands of elements could otherwise
    # reach while nothing is draining stdout.
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, cwd=project_dir, stdout=out, stderr=err)
        tick = progress.ticker("bst show")
        started = time.monotonic()
        # `UX-197`: `subprocess.run` kills the child if the caller leaves
        # the call by exception; the hand-rolled poll loop `UX-183` put
        # here to draw a ticker dropped that, so a Ctrl-C during a long
        # `bst show` returned to the shell and left `bst` running - the
        # orphan reproduced at 120s, still alive after the parent took
        # the KeyboardInterrupt. `BaseException`, not `Exception`,
        # because KeyboardInterrupt and SystemExit are exactly the two
        # this is about. Same contract `UX-157`/`UX-163` hold one phase
        # over.
        try:
            while proc.poll() is None:
                tick.note(f"{time.monotonic() - started:.0f}s elapsed")
                time.sleep(0.1)
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        finally:
            tick.done()
        out.seek(0)
        err.seek(0)
        stdout = out.read().decode("utf-8", errors="replace")
        stderr = err.read().decode("utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(
            f"bst show failed (exit {proc.returncode}) for targets {list(targets)}: "
            f"{stderr.strip()}"
        )
    return stdout


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
        if len(fields) != 7:
            # Defensive: a malformed/unexpected record (e.g. a future
            # bst version changing --format's output shape) should be
            # visible, not silently dropped or crash the whole run.
            print(f"warning: skipping malformed bst show record: {fields!r}", file=sys.stderr)
            continue

        name, key, kind, build_deps_raw, runtime_deps_raw, public_raw, vars_raw = (
            f.strip() for f in fields
        )
        if not name or name in seen_uids:
            continue
        seen_uids.add(name)

        elements.append({
            "uid": name,
            "cache_key": key or None,
            "requested_target": name in requested,
            # Real, *resolved* per-element `max-jobs` (UX-31, correcting
            # UX-22's own capture route) - what this element's native
            # build system was actually given, read from `%{vars}`. See
            # _parse_effective_max_jobs.
            "max_jobs": _parse_effective_max_jobs(vars_raw, public_raw),
            # UX-31: BuildStream's real per-element parallelism control.
            # True/False/None (absent) - carried separately from the
            # resolved number because it is the *cause*, and "pinned to
            # one job on purpose" is a different fact from "the project
            # default happens to be 1".
            "notparallel": _parse_notparallel(vars_raw),
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
    bst_options: Optional[Sequence[str]] = None,
) -> dict:
    """Run bst show and parse its output in one call - the entry point
    other tools/tests should import, rather than reaching for
    run_bst_show/build_graph separately.

    `bst_options` (`UX-377`) are the top-level options the build itself
    ran with, replayed here so the resolved values this reads describe
    that build rather than a fresh resolution. Empty for a graph
    extracted without a build behind it, which is the same thing it
    always did."""
    stdout = run_bst_show(project_dir, targets, bst_bin=bst_bin,
                          bst_options=bst_options)
    return build_graph(stdout, targets)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert real `bst show` output into graph/v9 JSON for bga.",
    )
    parser.add_argument("project_dir", help="Path to the BuildStream project directory.")
    parser.add_argument(
        "targets", nargs="+",
        help="Element(s) actually passed to the real bst build/show invocation "
             "being analyzed - these are marked requested_target: true.",
    )
    parser.add_argument("output_json", help="Path to write graph.json to.")
    parser.add_argument(
        "--bst-bin", default="bst",
        help="Path to the bst executable (default: bst, resolved via PATH).",
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
