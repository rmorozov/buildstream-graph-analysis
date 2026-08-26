"""UX-312's first clause: the trace read by Perfetto's own reader.

`UX-298` shipped the emitter with two recorded deviations, and round 43
called them load-bearing for everything built on top: **there was no
`trace_processor` round-trip**, so every claim about the wire format
rested on the in-repo decoder - which is written from the wire rules,
but is still `bga` checking `bga`. Four items (`UX-308`..`UX-311`)
then added annotations, flows, counters and an identity track on top of
that unproven base.

This file closes that half of the debt. `trace_processor_shell` is a
single static binary; when it is present the trace is loaded by
Perfetto's own reader and queried with Perfetto's own SQL, and the
answers are compared to what `bga` says it wrote.

**How to get it.** It is not vendored - an 11 MB binary in a repository
that declines a protobuf dependency would be a strange thing to add -
and it is not downloaded by the suite, because a guard that reaches the
network is a guard that fails for reasons unrelated to the code. Point
`BGA_TRACE_PROCESSOR` at one, or put `trace_processor_shell` on
`PATH`:

```text
curl -Lo trace_processor_shell \\
  https://commondatastorage.googleapis.com/perfetto-luci-artifacts/\\
v49.0/linux-amd64/trace_processor_shell
chmod +x trace_processor_shell
```

**What it found the first time it ran** (Perfetto v49.0-33a4fd078,
Trace Processor RPC API version 14, on `examples/06`'s capture): every
one of the four items' claims held. 826 slices, 836 flows, 538 counter
samples peaking at 20 on one `count`-united track, and **every**
annotation key resolving as `debug.<key>` in the `args` table -
including `debug.cmd` at 553 characters behind a slice name of 120,
which is the whole of `UX-308`'s argument, proven by the reader rather
than asserted by the writer.

**Still open, and not closeable here.** `UX-298`'s *other* deviation is
a one-time open of `ui.perfetto.dev`. This environment's network policy
refuses that host (and `get.perfetto.dev`) at the CONNECT stage, so it
cannot be done from here and is left recorded rather than quietly
dropped.
"""
import gzip
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from tools.bga_timeline import (  # noqa: E402
    ANNOTATION_CONTRACT, CONCURRENCY_COUNTER, render)

GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"


def _shell():
    """The binary, or `None`."""
    named = os.environ.get("BGA_TRACE_PROCESSOR")
    if named and os.path.isfile(named) and os.access(named, os.X_OK):
        return named
    return shutil.which("trace_processor_shell")


needs_trace_processor = pytest.mark.skipif(
    _shell() is None,
    reason="no trace_processor_shell (set BGA_TRACE_PROCESSOR or add it to PATH)")


# One of everything the four items emit, so the reader has something of
# each kind to disagree about: two elements with a dependency between
# them, a process that failed, one killed by a signal, one with no
# observed exit, and a command longer than the 120-character name.
LONG_CMD = ("cc -c " + "-I/usr/include/deeply/nested/path " * 5
            + "the-tail-that-tells-them-apart.c")

_LOG = """[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:base.bst] START Building
[wrapper][2026-08-21 12:00:02,100] INFO: [00:00:02][aaaaaaaa][   build:base.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:02,200] INFO: [00:00:02][bbbbbbbb][   build:app.bst] START Building
[wrapper][2026-08-21 12:00:06,200] INFO: [00:00:06][bbbbbbbb][   build:app.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:06,300] INFO: Return code: 0
"""


def _raw():
    lines = [
        "START pid=2 ppid=1 ts=1000.0 element=base.bst inv=a src=spine cmd=sh",
        "START pid=3 ppid=2 ts=1000.1 element=base.bst inv=a src=spine cmd=cc ok.c",
        "END pid=3 ppid=2 ts=1000.6 element=base.bst inv=a src=spine exit=0 "
        "utime=0.02 stime=0.01 maxrss_kb=4096 cmd=cc ok.c",
        "START pid=4 ppid=2 ts=1000.2 element=base.bst inv=a src=spine cmd=cc bad.c",
        "END pid=4 ppid=2 ts=1000.7 element=base.bst inv=a src=spine exit=1 "
        "utime=0.01 stime=0.01 maxrss_kb=2048 cmd=cc bad.c",
        "START pid=5 ppid=2 ts=1000.3 element=base.bst inv=a src=spine cmd=cc killed.c",
        "END pid=5 ppid=2 ts=1000.8 element=base.bst inv=a src=spine exit=signal:9 "
        "utime=0.01 stime=0.01 maxrss_kb=1024 cmd=cc killed.c",
        "END pid=2 ppid=1 ts=1001.0 element=base.bst inv=a src=spine exit=0 "
        "utime=0.05 stime=0.02 maxrss_kb=8192 cmd=sh",
        f"START pid=2 ppid=1 ts=1002.0 element=app.bst inv=b cmd={LONG_CMD}",
        f"END pid=2 ppid=1 ts=1003.0 element=app.bst inv=b utime=0.5 stime=0.1 "
        f"maxrss_kb=65536 cmd={LONG_CMD}",
        "START pid=3 ppid=1 ts=1003.5 element=app.bst inv=b cmd=cc never-exits.c",
    ]
    return "\n".join(lines) + "\n"


_GRAPH = {
    "elements": [
        {"uid": "base.bst", "cache_key": "k1", "requested_target": False,
         "element_kind": "cmake"},
        {"uid": "app.bst", "cache_key": "k2", "requested_target": True,
         "element_kind": "autotools"},
    ],
    "dependencies": [{"predecessor": "base.bst", "successor": "app.bst",
                      "dependency_type": "build"}],
    "run_identity_hash": "real-reader-fixture",
}

_CONTEXT = {
    "run_identity": {"manifest_hash": "hash-abc",
                     "project_identity": "examples/real-reader",
                     "targets": ["all.bst"], "project_git_commit": "c0ffee",
                     "scheduler": {"builders": 5}},
    "host_manifest": {"schema": "host/v1", "cpu_model": "Test CPU",
                      "cpu_count": 6, "memory_mb": 8192,
                      "kernel_release": "9.9.9", "distro_id": "test 1",
                      "toolchain": {"bst": "2.7.0"}},
    "build_outcome": {"failed_elements": [], "failed_count": 0,
                      "interrupted": False},
}


def _build(tmp, outcome=None, name="20260821T120000Z"):
    snapshot = tmp / name
    snapshot.mkdir()
    (snapshot / "build.log").write_text(_LOG, encoding="utf-8")
    shutil.copytree(GOLDEN, snapshot / "run")
    (snapshot / "run" / "expected_output.json").unlink(missing_ok=True)
    (snapshot / "run" / "graph.json").write_text(json.dumps(_GRAPH),
                                                 encoding="utf-8")
    context = json.loads(json.dumps(_CONTEXT))
    if outcome is not None:
        context["build_outcome"] = outcome
    (snapshot / "run" / "run-context.json").write_text(json.dumps(context),
                                                       encoding="utf-8")
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as out:
        out.write(_raw())
    trace = tmp / f"{name}.perfetto-trace.gz"
    return snapshot, trace, render(str(snapshot), str(trace))


@pytest.fixture(scope="module")
def queried(tmp_path_factory):
    shell = _shell()
    if shell is None:
        pytest.skip("no trace_processor_shell")
    tmp = tmp_path_factory.mktemp("realreader")
    _snapshot, trace, result = _build(tmp)
    # A second trace from an interrupted run: `incomplete_reason` is the
    # one contract key a finished run does not emit, so the coverage
    # clause takes the union of the two rather than pretending one
    # capture carries everything.
    _s2, stopped, _r2 = _build(
        tmp, outcome={"failed_elements": [], "failed_count": 0,
                      "interrupted": True},
        name="20260822T090000Z")

    def ask(sql, path=None):
        """One query, as rows of dicts. Perfetto's own SQL, its own
        reader - which is the point of this file."""
        done = subprocess.run(
            [shell, "-q", "/dev/stdin", str(path or trace)],
                              input=sql, capture_output=True, text=True,
                              timeout=180)
        assert done.returncode == 0, done.stderr
        lines = [line for line in done.stdout.strip().splitlines() if line]
        if not lines:
            return []
        header = [cell.strip('"') for cell in lines[0].split(",")]
        rows = []
        for line in lines[1:]:
            # Values are quoted only when they are strings; the fixture
            # has no commas inside one.
            cells = [cell.strip('"') for cell in line.split(",")]
            rows.append(dict(zip(header, cells)))
        return rows

    return {"result": result, "ask": ask, "trace": trace,
            "stopped": stopped}


@needs_trace_processor
class TestPerfettosOwnReaderAgrees:

    def test_it_loads_at_all(self, queried):
        """The clause `UX-298` could not write. A trace the emitter is
        happy with and the reader refuses is the failure mode this
        whole file exists to rule out."""
        rows = queried["ask"]("select count(*) as n from slice;")
        assert rows and int(rows[0]["n"]) == queried["result"]["slices"]

    def test_the_flow_table_holds_what_the_writer_counted(self, queried):
        rows = queried["ask"]("select count(*) as n from flow;")
        assert int(rows[0]["n"]) == queried["result"]["flows"]

    def test_the_dependency_arrow_points_the_way_the_graph_says(self, queried):
        rows = queried["ask"](
            "select extract_arg(o.arg_set_id,'debug.element') as source,"
            "       extract_arg(i.arg_set_id,'debug.element') as sink "
            "from flow f join slice o on o.id=f.slice_out "
            "join slice i on i.id=f.slice_in "
            "where extract_arg(o.arg_set_id,'debug.element') is not null;")
        assert {(r["source"], r["sink"]) for r in rows} == \
            {("base.bst", "app.bst")}

    def test_the_exec_chain_arrows_are_parent_to_child(self, queried):
        rows = queried["ask"](
            "select o.name as source, i.name as sink "
            "from flow f join slice o on o.id=f.slice_out "
            "join slice i on i.id=f.slice_in where o.name = 'sh';")
        assert sorted(r["sink"] for r in rows) == \
            ["cc bad.c", "cc killed.c", "cc ok.c"]

    def test_every_contract_key_resolves_through_extract_arg(self, queried):
        """`UX-308` asserted this through the in-repo decoder and
        recorded that it was unproven against Perfetto's own SQL. It is
        proven here: each key appears in `args` as `debug.<key>`."""
        seen = set()
        for path in (None, queried["stopped"]):
            rows = queried["ask"](
                "select distinct key from args where key like 'debug.%';",
                path)
            seen |= {row["key"][len("debug."):] for row in rows}
        documented = {key for key, _ in ANNOTATION_CONTRACT}
        assert documented - seen == set(), documented - seen
        assert seen - documented == set(), seen - documented

    def test_the_argv_tail_survives_behind_a_short_name(self, queried):
        """The item's own headline, read back by the reader: the name is
        cut at 120 and the annotation is not."""
        rows = queried["ask"](
            "select length(s.name) as name_len, "
            "length(extract_arg(s.arg_set_id,'debug.cmd')) as cmd_len "
            "from slice s where extract_arg(s.arg_set_id,'debug.cmd') "
            f"like '%{LONG_CMD[-20:]}';")
        assert rows, "the long command produced no slice"
        assert int(rows[0]["name_len"]) == 120
        assert int(rows[0]["cmd_len"]) == len(LONG_CMD) > 120

    def test_the_failed_processes_are_selectable(self, queried):
        rows = queried["ask"](
            "select s.name as name from slice s "
            "where extract_arg(s.arg_set_id,'debug.exit_status') "
            "not in ('0') order by name;")
        assert [r["name"] for r in rows] == ["cc bad.c", "cc killed.c"]

    def test_the_counter_track_is_a_counter_with_a_unit(self, queried):
        rows = queried["ask"](
            "select t.name as name, t.unit as unit, count(c.id) as samples, "
            "max(c.value) as peak from counter_track t "
            "left join counter c on c.track_id = t.id group by t.id;")
        assert len(rows) == 1, rows
        assert rows[0]["name"] == CONCURRENCY_COUNTER
        assert rows[0]["unit"] == "count"
        assert int(rows[0]["samples"]) == queried["result"]["counters"]
        assert float(rows[0]["peak"]) == queried["result"]["counter_peak"]

    def test_the_identity_track_answers_who_this_was(self, queried):
        rows = queried["ask"](
            "select extract_arg(s.arg_set_id,'debug.run') as run, "
            "extract_arg(s.arg_set_id,'debug.project') as project, "
            "extract_arg(s.arg_set_id,'debug.host_cpu_count') as cpus, "
            "extract_arg(s.arg_set_id,'debug.bst_version') as bst "
            "from slice s "
            "where extract_arg(s.arg_set_id,'debug.run') is not null;")
        assert len(rows) == 1, rows
        assert rows[0]["run"] == "20260821T120000Z"
        assert rows[0]["project"] == "examples/real-reader"
        assert int(rows[0]["cpus"]) == 6
        assert rows[0]["bst"] == "2.7.0"

    def test_the_lanes_carry_the_rank_the_writer_gave_them(self, queried):
        rows = queried["ask"](
            "select distinct key from args where key = 'sibling_order_rank';")
        assert rows, "the ordering hint did not survive the reader"

    def test_time_by_element_kind_is_a_question_it_can_answer(self, queried):
        """`UX-312`'s first canned question, run rather than described."""
        rows = queried["ask"](
            "select extract_arg(s.arg_set_id,'debug.element_kind') as kind, "
            "count(*) as tasks from slice s "
            "where extract_arg(s.arg_set_id,'debug.element') is not null "
            "group by kind order by kind;")
        assert {r["kind"] for r in rows} == {"autotools", "cmake"}
        assert sum(int(r["tasks"]) for r in rows) == 2

    def test_an_interrupted_run_says_so_where_the_reader_can_see_it(
            self, queried):
        """`UX-311`'s honesty clause, through Perfetto's own SQL: the
        reason is an annotation *and* the track's name."""
        rows = queried["ask"](
            "select s.name as name, "
            "extract_arg(s.arg_set_id,'debug.incomplete_reason') as reason "
            "from slice s where extract_arg(s.arg_set_id,'debug.run') "
            "is not null;", queried["stopped"])
        assert len(rows) == 1, rows
        assert rows[0]["reason"] == "interrupted"
        assert "interrupted" in rows[0]["name"]
