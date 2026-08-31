"""UX-434: the graph-shape query, run rather than read.

`graph-levels` answers "what does my graph look like, level by level".
Against a real capture of `examples/06` - a project whose whole point is
a six-deep chain - it returned **one row**:

```text
"depth","elements","seconds","on_path"
2,10,28.527000,0.000000
```

Two independent defects, both invisible to a static reader. `group by
depth` bound to `slice.depth` - Perfetto's own column, the slice's
*nesting* depth, 0 on every builder slice - which shadows the
`extract_arg(...) as depth` alias; and `sum()` over
`debug.on_critical_path`, which is emitted as the **string** `'true'` /
`'false'`, is 0 on every capture.

`test_the_questions_ask_what_the_trace_answers` checks the *vocabulary*
and every key here was correct. The query is well-formed, names only
real annotations, and returns a row. Only executing it can tell.

So these clauses execute it, against a `slice` table built here that has
**its own `depth` column**, which is the whole mechanism. SQLite is not
Perfetto, but the shadowing is plain SQL name resolution and SQLite
reproduces it exactly - measured, on the query as it was:

```text
OLD: [(0, 4, 0.0)]     # one row, on_path 0.0, from four elements at three depths
```

`TestTheQueryAnswersARealTrace` below runs the same query through the
real reader when this machine has one, so the emulation is anchored
rather than trusted.
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
sys.path.insert(0, str(REPO / "tests"))

import trace_processor  # noqa: E402

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: The one committed capture with an analysis beside it, so its slices
#: carry `debug.depth` and `debug.on_critical_path` at all - `UX-431`
#: built it for exactly this.
FIXTURE = REPO / "tests/fixtures/with_timeline"

#: The graph the fixture's analysis publishes: eleven elements over ten
#: distinct depths, with `codegen.bst` the one element off the critical
#: path. Written out rather than read from the analysis, because a guard
#: that derives its expectation from the thing under test asserts only
#: that two copies of one bug agree.
SHAPE = {
    0: (["toolchain.bst"], 1),
    1: (["codegen.bst", "core.bst"], 1),
    2: (["lib-a.bst"], 1),
    3: (["lib-b.bst"], 1),
    4: (["lib-c.bst"], 1),
    5: (["lib-d.bst"], 1),
    6: (["lib-e.bst"], 1),
    7: (["lib-f.bst"], 1),
    8: (["app.bst"], 1),
    9: (["all.bst"], 1),
}


def library():
    """The question library, as data, read by running the module."""
    script = ('const { QUESTIONS } = await import("./bga/viewer/questions.js");'
              'console.log(JSON.stringify(QUESTIONS));')
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=REPO,
                          timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def question(qid):
    for entry in library():
        if entry.get("id") == qid:
            return entry
    raise AssertionError(f"no question with id {qid!r}")


def _db(rows):
    """A `slice` table shaped like Perfetto's, and `extract_arg`.

    The columns that matter are `depth` - the slice's **nesting** depth,
    which is what a bare `depth` in a `group by` resolves to - and
    `arg_set_id`, which `extract_arg` reads. Every builder slice sits at
    nesting depth 0, which is why the collision produced exactly one
    group and not a plausible-looking few.
    """
    args = {}
    db = sqlite3.connect(":memory:")
    db.create_function("extract_arg", 2,
                       lambda set_id, key: args.get(set_id, {}).get(key))
    db.execute("create table slice (id integer, arg_set_id integer, "
               "dur integer, depth integer, name text, category text)")
    for index, (depth, element, on_path, dur) in enumerate(rows):
        args[index] = {"debug.depth": depth, "debug.element": element,
                       "debug.on_critical_path": on_path}
        db.execute("insert into slice values (?,?,?,?,?,?)",
                   (index, index, dur, 0, element, "bga,bst-builder"))
    # The wrapper span: category `bst-builder`, no `depth`. It is what
    # the query's `is not null` exists for, and leaving it out would let
    # a mutation removing that clause pass.
    args[len(rows)] = {"debug.element": None}
    db.execute("insert into slice values (?,?,?,?,?,?)",
               (len(rows), len(rows), 1, 0, "bst build all.bst",
                "bga,bst-builder"))
    return db


def _fixture_rows():
    """The fixture's graph, in the shape the trace carries it.

    `lib-a.bst` appears **twice**, at one depth. An element with more
    than one task in a run is ordinary - it is why `_plane1_flows` has a
    last-ending and a first-beginning rule - and it is what tells a
    count of elements from a count of slices. Without it, `count(x)` and
    `count(distinct x)` agree and neither `elements` nor `on_path` is
    guarded against the wrong one.
    """
    rows = []
    for depth, (elements, _on_path) in SHAPE.items():
        for element in elements:
            rows.append((depth, element,
                         "false" if element == "codegen.bst" else "true",
                         1_000_000_000))
            if element == "lib-a.bst":
                rows.append((depth, element, "true", 1_000_000_000))
    return rows


@needs_node
class TestTheGraphShapeQueryIsRun:

    def _answer(self):
        sql = question("graph-levels")["sql"].rstrip().rstrip(";")
        return _db(_fixture_rows()).execute(sql).fetchall()

    def test_one_row_per_level_and_not_one_row_in_total(self):
        answer = self._answer()
        assert len(answer) == len(SHAPE), (
            f"{len(answer)} row(s) for a graph {len(SHAPE)} levels deep - "
            f"a `group by` that binds to slice.depth gives exactly one, "
            f"which is what UX-434 was filed on: {answer}")
        assert [row[0] for row in answer] == sorted(SHAPE), answer

    def test_each_level_counts_its_own_elements(self):
        counts = {row[0]: row[1] for row in self._answer()}
        assert counts == {depth: len(elements)
                          for depth, (elements, _) in SHAPE.items()}, counts

    def test_the_critical_path_column_is_not_always_zero(self):
        """The second defect. `sum('true')` is 0, so this column read
        zero on every capture ever taken - including one where eight of
        ten elements were on the path."""
        on_path = {row[0]: row[3] for row in self._answer()}
        assert on_path == {depth: count
                           for depth, (_, count) in SHAPE.items()}, on_path
        assert any(value for value in on_path.values()), (
            "every level reports nothing on the critical path")

    def test_the_wrapper_span_is_not_a_level(self):
        """It carries the builder category and no depth, so a query that
        dropped the `is not null` would report a level of `None`."""
        assert None not in [row[0] for row in self._answer()]

    def test_no_question_groups_by_a_name_slice_defines(self):
        """The sweep the item asks for, executable rather than read.
        `graph-levels` was the only one; this is what keeps it so.

        `slice`'s own column names are the collision surface, and a
        query that groups by one of them is grouping by Perfetto's
        value however it aliased its own.
        """
        columns = {row[1] for row in
                   _db([]).execute("pragma table_info(slice)").fetchall()}
        offenders = {}
        for entry in library():
            sql = (entry.get("sql") or "").lower()
            for clause in ("group by", "order by"):
                if clause not in sql:
                    continue
                named = sql.split(clause, 1)[1].split(";")[0]
                named = named.replace("\n", " ").split("limit")[0]
                for token in named.replace(",", " ").split():
                    if token in columns and f"as {token}" in sql:
                        offenders.setdefault(entry["id"], []).append(token)
        assert offenders == {}, (
            f"a query aliases a name the slice table also defines and "
            f"then groups or orders by it, so the alias is shadowed: "
            f"{offenders}")


#: `UX-321` made this one gate, asked in one place, because the skip
#: census counts by reason and a second wording for "the same optional
#: tool is absent" splits one family in two. The wording this file first
#: coined did exactly that, and CI is where it showed: undeclared, the
#: census failed all four interpreters while every test passed.
READER = trace_processor.shell()
needs_reader = pytest.mark.skipif(
    READER is None, reason=trace_processor.REASON)


@needs_node
@needs_reader
class TestTheQueryAnswersARealTrace:
    """What anchors the emulation above. Skipped where the reader is not
    installed - which includes CI - so every property it checks is also
    checked against the SQLite table, and this is the clause that says
    the two agree.
    """

    def _rows(self, tmp_path):
        from tools.bga_timeline import render

        trace = tmp_path / "six.pftrace"
        render(str(FIXTURE), str(trace))
        sql = tmp_path / "q.sql"
        sql.write_text(question("graph-levels")["sql"], encoding="utf-8")
        done = subprocess.run([READER, "-q", str(sql), str(trace)],
                              capture_output=True, text=True, timeout=300)
        assert done.returncode == 0, done.stderr
        # Drop the header by position, not by name: keying on
        # `"graph_depth"` made a mutation that renamed the column redden
        # this clause for the wrong reason - the header parsed as a row.
        body = [line for line in done.stdout.splitlines()
                if line and not line.startswith("Loading")][1:]
        return [line.split(",") for line in body]

    def test_the_real_reader_gives_one_row_per_level(self, tmp_path):
        rows = self._rows(tmp_path)
        assert len(rows) == len(SHAPE), rows
        assert [int(row[0]) for row in rows] == sorted(SHAPE), rows

    def test_the_real_reader_counts_the_critical_path(self, tmp_path):
        on_path = {int(row[0]): int(row[3]) for row in self._rows(tmp_path)}
        assert on_path == {depth: count
                           for depth, (_, count) in SHAPE.items()}, on_path


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
