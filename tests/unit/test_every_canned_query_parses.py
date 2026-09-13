"""UX-818: every canned question parses, with and without an element.

`renderedSql` in `bga/viewer/questions.js` fills two tokens,
`{element}` and `{window}`; `tools.dev_perfetto_queries.rendered_sql`
is the Python mirror the dev tool calls. A question whose rendered SQL
still carries a stray token, or a stray brace, fails to *parse* -
`sqlite3`'s `EXPLAIN`, against a bare `:memory:` connection, catches
that without needing Perfetto's own tables or `extract_arg`: a bare
sqlite lacks both, so every question fails there too, just with
`no such table` / `no such column` / `no such function` rather than a
syntax error - the two are told apart by the message.
"""
import functools
import json
import pathlib
import shutil
import sqlite3
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.dev_perfetto_queries import rendered_sql

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: A window big enough that the fill is exercised, small enough it is
#: obviously synthetic.
BOUNDS = {"start_ns": 10_000, "end_ns": 20_000}

#: Trace-processor-only syntax a bare sqlite would reject as a genuine
#: syntax error rather than a missing-table/column/function one. None
#: measured across all 18 (see Outcome) - nothing to skip by name.
ALLOWED = ("no such table", "no such column", "no such function")


@functools.lru_cache(maxsize=1)
def library():
    """The question library, as data, read by running the module it
    lives in - the same approach
    `test_the_graph_shape_query_answers.py`'s `library()` uses."""
    script = ('const { QUESTIONS } = await import("./bga/viewer/questions.js");'
              'console.log(JSON.stringify(QUESTIONS));')
    done = subprocess.run([node, "--input-type=module", "-e", script],
                          capture_output=True, text=True, cwd=REPO,
                          timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def _ids():
    return [q["id"] for q in library()] if node else ["no-node"]


def _question(qid):
    return next(q for q in library() if q["id"] == qid)


@needs_node
@pytest.mark.parametrize("qid", _ids())
@pytest.mark.parametrize("element,bounds", [(None, None), ("storm.bst", BOUNDS)],
                         ids=["no-element", "with-element-and-bounds"])
def test_question_parses(qid, element, bounds):
    sql = rendered_sql(_question(qid), element, bounds)
    db = sqlite3.connect(":memory:")
    try:
        db.execute(f"EXPLAIN {sql}")
    except sqlite3.OperationalError as error:
        message = str(error)
        assert any(reason in message for reason in ALLOWED), \
            f"{qid} ({element!r}): {message}"
