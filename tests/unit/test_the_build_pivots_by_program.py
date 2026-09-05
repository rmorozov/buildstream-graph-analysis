"""UX-433: which *program* is this build made of?

The question a reader wants of Plane 2 is a pivot - cpu, memory and wall
time per executable, argv stripped. Nothing in the library answered it
and no query could, because no annotation named an executable.

The nearest was `element-commands`, which groups by `s.name`: the whole
command line, 14,424 near-unique strings on the audited capture, so one
row per invocation and never one per program. `debug.cmd` was removed by
`UX-333` and stays removed - the full argv cost +75.1% when kept beside
the interned name. This is a short key instead, measured here rather
than assumed:

```text
                                trace bytes    over no annotation
  no annotation                     486,336
  debug.exe, basename               531,322    +9.2%
  debug.exe, the path as exec'd     546,877    +12.4%
```

on the 1,202-element two-plane fixture with twelve distinct programs.
**The path, not the basename**, and the 3.2 points between them is what
that decision costs: a query can take a basename from a path and nothing
can recover a path from a basename, so `/usr/bin/cc` and a compiler's own
`/usr/lib/gcc/.../cc1` stay two programs rather than one answer and one
lost distinction.

The clauses below run the two shipped queries rather than reading them -
against a SQLite `slice` table, the same instrument `UX-434` built, so
the pivot is exercised where CI can run it.
"""
import json
import pathlib
import shutil
import sqlite3
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tools.bga_timeline import PLANE2_ANNOTATIONS, _executable, render

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from test_the_slice_says_what_bga_knows import decode

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: A toolchain's worth, and deliberately two that share a basename
#: family - `cc` and `cc1` are what the path-versus-basename decision is
#: about, and a fixture without them cannot show it.
PROGRAMS = ("/usr/bin/cc", "/usr/lib/gcc/x86_64-linux-gnu/12/cc1",
            "/usr/bin/ld", "/bin/sh")


@pytest.fixture(scope="module")
def trace(tmp_path_factory):
    into = tmp_path_factory.mktemp("pivot")
    snapshot = pages.scale_two_plane_snapshot(into, per_element=4,
                                              programs=PROGRAMS)
    out = into / "two.pftrace"
    render(str(snapshot), str(out))
    return decode(out)


class TestTheExecutableIsOnEverySlice:

    def test_the_key_is_declared(self):
        assert "exe" in dict(PLANE2_ANNOTATIONS), (
            "no annotation names an executable, so no query can pivot on "
            "one - which is the whole of UX-433")

    def test_argv_is_stripped_and_the_path_is_not(self):
        assert _executable("/usr/bin/cc -c f0.c -o f0.o") == "/usr/bin/cc"
        assert _executable("/usr/lib/gcc/12/cc1") == "/usr/lib/gcc/12/cc1", (
            "the path was reduced to a basename, so `cc` and `cc1` under "
            "different prefixes can no longer be told apart")

    def test_a_record_with_no_command_carries_no_key(self):
        """Absent, not empty - the rule every annotation beside it
        follows. An empty string would group as a program named ''."""
        assert _executable("") is None
        assert _executable(None) is None

    def test_every_process_slice_carries_it(self, trace):
        processes = [event for event in trace["events"]
                     if any("native-process" in category
                            for category in event["categories"])]
        assert processes, "the fixture rendered no Plane 2 slices"
        missing = [event["name"] for event in processes
                   if "exe" not in event["args"]]
        assert missing == [], missing[:3]
        assert {event["args"]["exe"] for event in processes} == set(PROGRAMS)

    def test_it_is_not_the_slice_name(self, trace):
        """The defect restated: the name is the command line, which is
        why grouping by it answers per invocation."""
        processes = [event for event in trace["events"]
                     if any("native-process" in category
                            for category in event["categories"])]
        names = {event["name"] for event in processes}
        exes = {event["args"]["exe"] for event in processes}
        assert len(names) > len(exes) * 3, (
            f"{len(names)} distinct slice names against {len(exes)} "
            f"programs - this fixture no longer shows the two apart")


def _library():
    script = ('const { QUESTIONS } = await import("./bga/viewer/questions.js");'
              'console.log(JSON.stringify(QUESTIONS));')
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=REPO,
                          timeout=120)
    assert done.returncode == 0, done.stderr
    return {entry["id"]: entry for entry in json.loads(done.stdout)}


def _db(rows):
    """A `slice` table with Plane 2's annotations, and `extract_arg`."""
    args = {}
    db = sqlite3.connect(":memory:")
    db.create_function("extract_arg", 2,
                       lambda set_id, key: args.get(set_id, {}).get(key))
    db.execute("create table slice (id integer, arg_set_id integer, "
               "dur integer, depth integer, name text, category text)")
    for index, (element, exe, command, dur, cpu, rss) in enumerate(rows):
        args[index] = {"debug.element": element, "debug.exe": exe,
                       "debug.cpu_us": cpu, "debug.max_rss_kb": rss}
        db.execute("insert into slice values (?,?,?,?,?,?)",
                   (index, index, dur, 0, command, "bga,native-process"))
    return db


#: Two programs, four invocations, two elements - so a query that
#: answered per invocation would give four rows where the pivot gives
#: two, and `max()` over RSS is a different number from `sum()`.
ROWS = [
    ("a.bst", "/usr/bin/cc", "/usr/bin/cc -c f0.c", 1_000_000_000,
     500_000, 1024),
    ("a.bst", "/usr/bin/cc", "/usr/bin/cc -c f1.c", 3_000_000_000,
     900_000, 4096),
    ("b.bst", "/usr/bin/ld", "/usr/bin/ld -o out", 2_000_000_000,
     100_000, 2048),
    ("b.bst", "/usr/bin/cc", "/usr/bin/cc -c f2.c", 1_000_000_000,
     200_000, 512),
]


@needs_node
class TestThePivotAnswersPerProgram:

    def _run(self, qid, element=None):
        sql = _library()[qid]["sql"].rstrip().rstrip(";")
        if element is not None:
            sql = sql.replace("{element}", element)
        return _db(ROWS).execute(sql).fetchall()

    def test_one_row_per_program_and_not_per_invocation(self):
        answer = self._run("cost-by-executable")
        assert len(answer) == 2, (
            f"{len(answer)} rows for two programs over four invocations - "
            f"the pivot is answering per invocation again: {answer}")
        assert [row[0] for row in answer] == ["/usr/bin/cc", "/usr/bin/ld"]

    def test_the_runs_and_the_seconds_are_summed(self):
        by_exe = {row[0]: row for row in self._run("cost-by-executable")}
        assert by_exe["/usr/bin/cc"][1] == 3, by_exe
        assert by_exe["/usr/bin/cc"][2] == pytest.approx(5.0)
        assert by_exe["/usr/bin/cc"][3] == pytest.approx(1.6)

    def test_peak_rss_is_a_maximum_and_not_a_sum(self):
        """Two processes' resident sets were never held at once, so a
        sum states a memory figure no moment of the build had."""
        by_exe = {row[0]: row for row in self._run("cost-by-executable")}
        assert by_exe["/usr/bin/cc"][4] == 4096, by_exe

    def test_the_element_scoped_twin_answers_at_the_program_grain(self):
        """`UX-448` shipped what `UX-433` held back.

        The clause here used to be its opposite - the pivot was kept
        *out* of the library, because `UX-368`'s rule is that a
        question no finding points at is a question nobody arrives at,
        and at the time no claim was about what an element ran.
        `latent-heavies` carries both grains now, so the absence guard
        would be asserting a state the page has deliberately left; it
        is replaced by the clause that says the query is right rather
        than deleted outright.

        `ROWS` gives `a.bst` two `cc` invocations and one `ld`: the
        distinction the whole pivot is for, and the one that tells a
        query grouping by program from one grouping by command line.
        """
        answer = self._run("executables-in-element", "a.bst")
        assert [row[0] for row in answer] == ["/usr/bin/cc"], (
            f"the element-scoped pivot is answering per invocation, or "
            f"reaching outside the element it was aimed at: {answer}")
        assert answer[0][1] == 2, f"two invocations, one program: {answer}"

    def test_a_slice_with_no_executable_is_not_a_program(self):
        """A record that carried no command would otherwise group as a
        program whose name is NULL."""
        rows = ROWS + [("c.bst", None, "?", 9_000_000_000, 1, 1)]
        sql = _library()["cost-by-executable"]["sql"].rstrip().rstrip(";")
        assert None not in [row[0] for row in _db(rows).execute(sql)]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
