#!/usr/bin/env python3
"""UX-465: a BuildStream project `bst build` accepts, from a topology spec.

Three generators in this tree synthesise the *ingested* form directly -
`tests/fixtures/topologies.py`, `tools/gen_synthetic_scale_run.py`,
`tests/fixtures/synthetic_multi_subproject/build_model.py`. All three
start after `bst` would have run. So Plane 1's real scheduler log,
Plane 2's `LD_PRELOAD` hook and Plane 3's ptrace spine are exercised by
nine hand-written projects and by nothing else, and `UX-463`'s axes D
(outcome), F (sandbox profile) and G (scale) have no generator at all.

Axis F is the one that cannot be faked: a process storm and a staging
of many small files are things the hook and the spine *observe*. A
synthesised trace can only assert what its author already believed
about them, which is `UX-120`'s inert-detector problem one level down.

One language, two halves
------------------------
The spec's `graph` is `tests/fixtures/topologies.py`'s graph verbatim -
the same `{"uid", "element_kind", "requested_target"}` elements and
`{"predecessor", "successor", "dependency_type"}` edges - so a curated
fixture and a generated project describe the same shape, and
`spec_from_topology` turns one into the other.

The *trace* half is deliberately not shared. A trace is what a build
produces; a spec is what it consumes. What the spec carries instead is
`work`: the seconds, processes, files and failure each element should
cost, which is what a real build turns back into a trace.

What a generated project is not
-------------------------------
Not a worked example. `examples/01..09` are documentation as much as
fixtures and this replaces none of them (`UX-465` Out of Scope). This
is for the cases a document should not have to carry: a build that
fails, a staging of 60,000 inodes, a shape nobody wants to hand-write.
"""
import argparse
import json
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]

#: Not a contract id. `bga.contracts.inventory()` is the set a release
#: records, and it walks the `bga` package; an id of the `name/vN` shape
#: stamped anywhere in the source must appear there (`UX-248`). This
#: format is a dev tool's *input* - nothing writes it into a capture and
#: no released artifact carries it - so it takes a plain integer rather
#: than inventing an owner in `bga/` for something `bga/` does not own.
SPEC_VERSION = 1

#: Applets `stage_runtimes.sh` puts in every example's runtime, for the
#: same reason: BuildStream's sandbox is assembled purely from staged
#: dependencies, so something has to provide `/bin/sh`.
APPLETS = ("sh", "sleep", "true", "env", "cat", "mkdir", "touch", "seq")

RUNTIME_UID = "runtime.bst"
TARGET_UID = "all.bst"


class SpecError(ValueError):
    """The spec cannot be turned into a project, and why."""


# --- the spec ---------------------------------------------------------

def spec_from_topology(topology, name, work=None):
    """A spec from one `tests/fixtures/topologies.py` factory result.

    Durations come from the topology's own spans, which for a synthetic
    topology *are* the intended per-element seconds rather than a
    measurement of anything - the whole point of the curated half is
    that its timings are written rather than observed.
    """
    _run_context, graph, trace = topology
    seconds = {}
    for span in trace.get("spans", []):
        uid = str(span["task_key"]).split("|")[0]
        seconds[uid] = max(seconds.get(uid, 0.0), span["dur_us"] / 1e6)
    merged = {uid: {"seconds": round(value, 3)} for uid, value in seconds.items()}
    for uid, extra in (work or {}).items():
        merged.setdefault(uid, {}).update(extra)
    return {"spec_version": SPEC_VERSION, "name": name, "graph": graph,
            "work": merged}


def validate(spec):
    """`spec`, or a `SpecError` naming the first thing wrong with it."""
    if spec.get("spec_version") != SPEC_VERSION:
        raise SpecError(
            f"spec_version is {spec.get('spec_version')!r}, expected "
            f"{SPEC_VERSION!r}")
    graph = spec.get("graph") or {}
    uids = [e["uid"] for e in graph.get("elements") or []]
    if not uids:
        raise SpecError("the spec names no elements")
    if len(set(uids)) != len(uids):
        raise SpecError("two elements share a uid")
    for reserved in (RUNTIME_UID, TARGET_UID):
        if reserved in uids:
            raise SpecError(
                f"{reserved} is written by the generator; the spec must not "
                f"declare it")
    known = set(uids)
    for edge in graph.get("dependencies") or []:
        for end in ("predecessor", "successor"):
            if edge[end] not in known:
                raise SpecError(f"edge names {edge[end]!r}, which is not an element")
    for uid in spec.get("work") or {}:
        if uid not in known:
            raise SpecError(f"work names {uid!r}, which is not an element")
    return spec


# --- the emitter ------------------------------------------------------

def _commands(work):
    """The `install-commands` for one element's declared work.

    Every knob is a real command in a real sandbox, which is the point:
    `processes` makes the hook see a process storm and `files` makes it
    see staging, and neither can be asserted into existence from
    outside.
    """
    seconds = float(work.get("seconds", 0.1) or 0)
    processes = int(work.get("processes", 0) or 0)
    files = int(work.get("files", 0) or 0)
    lines = []
    if files:
        lines.append('mkdir -p "%{install-root}/staged"')
        lines.append(
            f'for i in $(seq 1 {files}); do '
            f'touch "%{{install-root}}/staged/f$i"; done')
    if processes:
        # Concurrent, so the hook sees them overlap rather than queue.
        each = max(seconds / 2, 0.05)
        lines.append(
            f'i=0; while [ $i -lt {processes} ]; do '
            f'sh -c "sleep {each:.2f}" & i=$((i+1)); done; wait')
        seconds = max(seconds - each, 0.0)
    if seconds > 0:
        lines.append(f"sleep {seconds:.2f}")
    if work.get("fails"):
        # UX-463's axis D. Last, so everything above really ran first -
        # a build that fails at once exercises none of the capture.
        lines.append("exit 1")
    return lines or ["true"]


def _scalar(text):
    """One shell command as a YAML single-quoted scalar.

    Not decoration. The first version wrote commands inside *double*
    quotes and the process-storm command contains a `sh -c "..."`, so
    the inner quote closed the scalar and bst refused the whole project
    with `did not find expected key`. Single-quoted YAML has exactly one
    escape - a doubled quote - and no interpolation, so a shell command
    survives it whatever it contains.
    """
    return "'" + str(text).replace("'", "''") + "'"


def _element_yaml(uid, kind, depends, work, source=None):
    lines = [f"# Generated by tools/bga_gen_project.py, spec_version {SPEC_VERSION}.",
             f"kind: {kind}"]
    if source is not None:
        # Project-root relative, which is why the `files/` is here and
        # not only in the directory the generator created: bst resolves
        # `path` against project.conf, not against the element.
        lines += ["sources:", "- kind: local", f"  path: files/{source}"]
    if depends:
        lines.append("depends:")
        for name in depends:
            lines += [f"- filename: {name}", "  type: build"]
    if kind == "manual":
        lines += ["config:", "  install-commands:"]
        lines += [f"  - {_scalar(command)}" for command in _commands(work)]
    return "\n".join(lines) + "\n"


def write_project(spec, out, busybox=None):
    """Write the project `spec` describes under `out`, and return it."""
    validate(spec)
    graph = spec["graph"]
    work = spec.get("work") or {}
    sources = spec.get("sources") or {}
    out = pathlib.Path(out)
    if out.exists():
        shutil.rmtree(out)
    (out / "elements").mkdir(parents=True)

    _write_runtime(out, busybox)
    for name, path in sorted({v: v for v in sources.values()}.items()):
        directory = out / "files" / path
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "content.txt").write_text(f"{name}\n", encoding="utf-8")

    parents = {}
    for edge in graph.get("dependencies") or []:
        parents.setdefault(edge["successor"], []).append(edge["predecessor"])

    for element in graph["elements"]:
        uid = element["uid"]
        kind = element.get("element_kind") or "manual"
        depends = sorted(parents.get(uid, []))
        source = sources.get(uid)
        if kind == "manual" or source is None:
            depends = [RUNTIME_UID] + depends
        if kind == "import" and source is None:
            # An `import` with nothing to import is not a project bst
            # will load, so a structural element the spec did not give
            # a source gets one of its own.
            source = f"import/{uid[:-4]}"
            directory = out / "files" / source
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{uid[:-4]}.txt").write_text(uid + "\n", encoding="utf-8")
            depends = []
        (out / "elements" / uid).write_text(
            _element_yaml(uid, kind, depends, work.get(uid, {}), source),
            encoding="utf-8")

    targets = [e["uid"] for e in graph["elements"]] or []
    (out / "elements" / TARGET_UID).write_text(
        "# Real build target: every element the spec named.\n"
        "kind: stack\ndepends:\n"
        + "".join(f"- {uid}\n" for uid in sorted(targets)),
        encoding="utf-8")
    (out / "project.conf").write_text(
        f"# Generated by tools/bga_gen_project.py, spec_version {SPEC_VERSION}.\n"
        f"name: {spec['name']}\nmin-version: 2.0\nelement-path: elements\n",
        encoding="utf-8")
    (out / "spec.json").write_text(json.dumps(spec, indent=2) + "\n",
                                   encoding="utf-8")
    return out


def _write_runtime(out, busybox=None):
    """The shell every `manual` element runs its commands with.

    `examples/stage_runtimes.sh`'s reason, for the same reason: the
    sandbox is assembled purely from staged dependencies, so nothing
    from the host provides `/bin/sh` unless an element does.
    """
    binaries = out / "files" / "runtime" / "bin"
    binaries.mkdir(parents=True)
    busybox = busybox or shutil.which("busybox")
    if busybox is None:
        raise SpecError(
            "no busybox on PATH: the generated project needs a static shell "
            "to stage, the same one examples/stage_runtimes.sh stages")
    for applet in APPLETS:
        shutil.copy2(busybox, binaries / applet)
    (out / "elements" / RUNTIME_UID).write_text(
        "# Provides /bin/sh for every manual element here. Staged from a\n"
        "# static busybox, never committed - examples/stage_runtimes.sh's\n"
        "# reason, and UX-189's rule.\n"
        "kind: import\nsources:\n- kind: local\n  path: files/runtime\n",
        encoding="utf-8")


# --- cli --------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spec", help="a project-spec/v1 document")
    parser.add_argument("--from-topology",
                        help="a factory name in tests/fixtures/topologies.py")
    parser.add_argument("--out", required=True, help="where to write the project")
    parser.add_argument("--print-spec", action="store_true",
                        help="write the spec to stdout instead of a project")
    args = parser.parse_args(argv)

    if bool(args.spec) == bool(args.from_topology):
        parser.error("give exactly one of --spec and --from-topology")
    if args.from_topology:
        sys.path.insert(0, str(REPO))
        from tests.fixtures import topologies
        factory = getattr(topologies, args.from_topology, None)
        if factory is None:
            parser.error(f"no factory named {args.from_topology!r}")
        produced = factory()
        topology = produced[0] if isinstance(produced[0], tuple) else produced
        spec = spec_from_topology(topology, args.from_topology.replace("_", "-"))
    else:
        spec = json.loads(pathlib.Path(args.spec).read_text(encoding="utf-8"))

    if args.print_spec:
        print(json.dumps(validate(spec), indent=2))
        return 0
    try:
        out = write_project(spec, args.out)
    except SpecError as complaint:
        print(f"cannot generate: {complaint}", file=sys.stderr)
        return 2
    print(json.dumps({"out": str(out), "name": spec["name"],
                      "elements": len(spec["graph"]["elements"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
