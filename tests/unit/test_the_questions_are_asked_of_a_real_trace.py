"""UX-432: the harness that runs the library, and what it must not blur.

`test_the_questions_ask_what_the_trace_answers.py` holds the library's
vocabulary against the emitter's, statically, everywhere. It cannot say
whether a question *returns* anything - and round 69 found that three
did not, on a capture with both planes in it, because no machine this
project had run on had `trace_processor_shell` and the gate that would
have executed them skipped instead.

`tools/dev_perfetto_queries.py` is that execution as a command. These
clauses hold the two distinctions the tool exists to make, and they run
without the reader by standing a stub in its place - the reader is what
the tool needs, not what these claims are about.

**An empty answer and a refused query are different findings.** Empty
means the trace cannot answer; an error means the question is malformed.
A harness that reported them the same way would have told round 69 that
fourteen questions were fine.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "dev_perfetto_queries.py"

#: A stub reader. It answers the element-pick query with one element and
#: everything else per the mode named in the environment, so a clause can
#: choose what the reader "found" without a trace or a binary.
STUB = '''#!/usr/bin/env python3
import os, sys
sql = ""
for i, arg in enumerate(sys.argv):
    if arg == "-q":
        sql = open(sys.argv[i + 1]).read()
mode = os.environ.get("STUB_MODE", "rows")

# The element pick. `limit 1` is what separates it from the questions,
# several of which also group by element. The two orderings answer
# **differently**, so a pick that stops preferring an element which
# waited is visible here rather than indistinguishable.
if "group by element" in sql and "limit 1" in sql:
    if "waits desc" in sql:
        print('"element","waits","total"')
        print('"core.bst","1","900"')
    else:
        print('"element","total"')
        print('"all.bst","900"')
    sys.exit(0)

# An unfilled placeholder, answered as its own row and nothing else, so
# the assertion reads it rather than a plausible row in front of it.
if "{element}" in sql:
    print('"element","seconds"')
    print('"NO-SUBSTITUTION","0"')
    sys.exit(0)

if mode == "error":
    sys.stderr.write("SQL error: no such column: nonsense\\n")
    sys.exit(1)
if mode == "empty":
    sys.exit(0)
print('"element","seconds"')
print('"core.bst","1.5"')
'''


@pytest.fixture
def stub(tmp_path):
    path = tmp_path / "trace_processor_shell"
    path.write_text(STUB, encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture
def trace(tmp_path):
    """The tool checks the file exists; the stub never reads it."""
    path = tmp_path / "fake.pftrace"
    path.write_bytes(b"\x00")
    return path


def run(stub, trace, mode, tmp_path, element=None):
    argv = [sys.executable, str(TOOL), str(trace), "--format", "json",
            "--fetch-into", str(tmp_path / "cache")]
    if element:
        argv += ["--element", element]
    # The real environment, plus the stub ahead of it: the tool reads
    # the question library by running `node`, so a stripped PATH tests
    # nothing about the tool and everything about the fixture.
    done = subprocess.run(
        argv, capture_output=True, text=True, cwd=REPO, timeout=300,
        env={**os.environ, "PATH": f"{stub.parent}:{os.environ['PATH']}",
             "STUB_MODE": mode, "BGA_TRACE_PROCESSOR": str(stub)})
    assert done.stdout.strip(), (
        f"the tool printed nothing; exit {done.returncode}, "
        f"stderr: {done.stderr[-400:]}")
    return done


class TestEmptyAndBrokenAreDifferentFindings:
    def test_a_question_that_answers_nothing_is_reported_empty(
            self, stub, trace, tmp_path):
        done = run(stub, trace, "empty", tmp_path)
        assert done.returncode == 0, done.stderr
        seen = json.loads(done.stdout)
        assert seen["errors"] == [], (
            f"an empty answer was reported as an error: {seen['errors']}")
        assert len(seen["empty"]) == seen["questions"], (
            f"only {len(seen['empty'])} of {seen['questions']} reported empty")

    def test_a_question_the_reader_refuses_is_reported_broken(
            self, stub, trace, tmp_path):
        done = run(stub, trace, "error", tmp_path)
        seen = json.loads(done.stdout)
        assert seen["empty"] == [], (
            f"a refused query was reported as empty: {seen['empty']}")
        assert len(seen["errors"]) == seen["questions"]
        assert done.returncode == 1, (
            "a refused query must fail the command; got "
            f"{done.returncode}")

    def test_the_two_do_not_share_an_exit_code(self, stub, trace, tmp_path):
        empty = run(stub, trace, "empty", tmp_path).returncode
        broken = run(stub, trace, "error", tmp_path).returncode
        assert empty != broken, (
            f"empty and refused both exit {empty} - the distinction this "
            f"tool exists to make is invisible to a caller")


class TestTheQuestionsAreAskedOfThisCapture:
    def test_every_question_in_the_library_is_run(self, stub, trace, tmp_path):
        seen = json.loads(run(stub, trace, "rows", tmp_path).stdout)
        ids = [row["id"] for row in seen["results"]]
        assert "graph-levels" in ids and "peak-rss" in ids
        assert len(ids) == len(set(ids)) == seen["questions"]

    def test_the_element_placeholder_is_filled_from_the_trace(
            self, stub, trace, tmp_path):
        """`UX-369`'s rule reaches the harness.

        The stub emits a `NO-SUBSTITUTION` row for any query still
        carrying an unfilled `{element}` - so a tool that stopped
        substituting reddens here rather than silently asking about
        nothing.
        """
        seen = json.loads(run(stub, trace, "rows", tmp_path).stdout)
        blank = [row["id"] for row in seen["results"]
                 if (row["first"] or {}).get("element") == "NO-SUBSTITUTION"]
        assert not blank, f"asked with an unfilled placeholder: {blank}"

    def test_the_pick_prefers_an_element_that_waited(
            self, stub, trace, tmp_path):
        """Two of the three element-taking questions ask what it waited
        for, so the root - which waits for nothing - answers them empty
        however long it ran. Both wrong picks were made while writing
        this tool.
        """
        seen = json.loads(run(stub, trace, "rows", tmp_path).stdout)
        assert seen["element"] == "core.bst", (
            f"picked {seen['element']!r}; a pick that ignores whether the "
            f"element waited reports answerable questions as empty")

    def test_an_explicit_element_wins(self, stub, trace, tmp_path):
        seen = json.loads(
            run(stub, trace, "rows", tmp_path, element="other.bst").stdout)
        assert seen["element"] == "other.bst"
