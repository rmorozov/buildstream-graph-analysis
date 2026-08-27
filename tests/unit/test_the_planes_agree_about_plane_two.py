"""UX-329: the terminal and the viewer say the same thing about Plane 2.

`bga view --help` promises that "the viewer and the terminal can never
disagree about what a run says". On a snapshot holding a Plane 2 report
they did:

```text
$ bga analyze @last --format json | jq .plane2_coverage
null
$ (the page, same alias, same schema)
{"processes": 813, "opens_coverage": 1.0, "source": {…}}
```

because `bga correlate` and `bga view` both found the sibling
`plane2.json` and attached it, and `analyze` — the third reader — asked
for `--plane2` and hinted at nothing. Three readers, two copies of the
policy, and the copies disagreed.

The second half is the **absence grammar**. One sentence used to cover
three situations a reader cannot tell apart from it:

* Plane 2 was never captured — a machine that could not trace;
* Plane 2 was captured and its raw log was dropped — a complete
  measurement missing only its timeline;
* Plane 2 was captured and this report was told not to read it.

The first is a problem, the second is not, and the third is the
reader's own flag. `UX-156`'s rule — absence is stated, not implied —
applied to the plane.
"""
import contextlib
import io
import json
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import plane2, run_store  # noqa: E402
from tools.bga_view import payloads  # noqa: E402

FIXTURE = REPO / "tests/fixtures/macro_micro"
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"


def _terminal(run, *extra):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        with contextlib.redirect_stderr(io.StringIO()):
            main(["analyze", str(run), "--format", "json", *extra])
    return json.loads(buffer.getvalue())


def _text(run, *extra):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        with contextlib.redirect_stderr(io.StringIO()):
            main(["analyze", str(run), *extra])
    return buffer.getvalue()


@pytest.fixture
def snapshot(tmp_path):
    """A run inside a snapshot, with a Plane 2 report beside it and no
    raw log - the shape the friction was found on."""
    snap = tmp_path / "20260101T000000Z"
    snap.mkdir()
    shutil.copytree(FIXTURE / "run", snap / "run")
    shutil.copy(FIXTURE / "plane2.json", snap / run_store.PLANE2_NAME)
    return snap


class TestTheTerminalAndThePageAgree:

    def test_plane2_coverage_is_byte_identical(self, snapshot):
        """The acceptance test, and the help's promise made checkable."""
        run = snapshot / "run"
        terminal = json.dumps(_terminal(run).get("plane2_coverage"),
                              sort_keys=True)
        page = json.dumps(payloads(str(run))["report.json"].get(
            "plane2_coverage"), sort_keys=True)
        assert terminal == page, (
            f"analyze and view publish different Plane 2 coverage for one "
            f"run:\n  analyze: {terminal}\n  view:    {page}")
        assert terminal != "null", (
            "both publish nothing, so the clause is vacuous - the fixture "
            "has a plane2.json beside it and both readers should find it")

    def test_the_absence_sentence_is_the_same_one(self, snapshot):
        run = snapshot / "run"
        assert (_terminal(run).get("plane2_absence")
                == payloads(str(run))["report.json"].get("plane2_absence"))

    def test_one_discovery_function_serves_both(self):
        """The mechanism, not just its result: two copies of a policy is
        what let them drift, so there is one and it is named."""
        source = (REPO / "tools/bga_view.py").read_text(encoding="utf-8")
        assert "plane2_shape.attachable(run)" in source, (
            "the viewer no longer routes through bga.plane2.attachable; a "
            "second copy of the discovery is exactly what UX-329 was")
        cli = (REPO / "bga/cli.py").read_text(encoding="utf-8")
        assert "plane2_shape.attachable(" in cli


class TestAnalyzeFindsTheSibling:

    def test_it_attaches_without_being_told(self, snapshot):
        assert _terminal(snapshot / "run").get("plane2_coverage"), (
            "`bga analyze` on a snapshot with a Plane 2 report beside it "
            "still publishes nothing - the UX-329 defect")

    def test_an_explicit_plane2_still_wins(self, snapshot, tmp_path):
        """The override has to keep overriding: a caller naming a report
        means that report, not the one the store happens to hold."""
        other = tmp_path / "other.json"
        other.write_text(json.dumps({
            "by_element": {}, "per_element_parallelism": [],
            "cpu_time": {"per_element": {}},
            "declared_vs_used": {"unused_candidates": []},
            "stream_coverage": {"processes": 7, "opens_coverage": 0.5},
        }), encoding="utf-8")
        coverage = _terminal(snapshot / "run", "--plane2", str(other))
        assert coverage["plane2_coverage"]["processes"] == 7

    def test_no_plane2_declines_and_says_so(self, snapshot):
        report = _terminal(snapshot / "run", "--no-plane2")
        assert not report.get("plane2_coverage")
        assert report["plane2_absence"] == plane2.DECLINED

    def test_a_run_outside_a_store_attaches_nothing(self):
        """`sibling_plane2` is a fact about the capture, not a reward
        for using the store - and a bare run directory has no sibling."""
        assert plane2.attachable(str(GOLDEN)) == (None, None)


class TestTheThreeAbsencesAreThreeSentences:

    def test_never_captured(self):
        assert plane2.absence(str(GOLDEN)) == plane2.NOT_CAPTURED

    def test_captured_but_the_raw_log_was_not_kept(self, snapshot):
        assert plane2.absence(str(snapshot / "run")) == plane2.CAPTURED_NO_RAW_LOG

    def test_captured_with_its_log_is_no_absence_at_all(self, snapshot):
        (snapshot / run_store.RAW_LOG_NAME).write_bytes(b"\x1f\x8b")
        assert plane2.absence(str(snapshot / "run")) is None

    def test_the_three_are_actually_different_sentences(self):
        """The mutation this file exists for is collapsing them, and a
        clause that only checked "a sentence is printed" would not see
        it."""
        sentences = {plane2.NOT_CAPTURED, plane2.CAPTURED_NO_RAW_LOG,
                     plane2.DECLINED}
        assert len(sentences) == 3, (
            "two of the three absence sentences are the same string, which "
            "is the defect UX-329 was filed for")
        assert "not captured" in plane2.NOT_CAPTURED
        assert "was captured" in plane2.CAPTURED_NO_RAW_LOG, (
            "the captured-but-no-log sentence no longer says the plane was "
            "captured, which is the half a reader needs")

    def test_the_terminal_prints_it(self, snapshot):
        assert plane2.CAPTURED_NO_RAW_LOG in _text(snapshot / "run")

    def test_the_terminal_says_nothing_when_there_is_no_absence(self, snapshot):
        """A report that announced an absence it does not have would be
        the same defect wearing the opposite sign."""
        (snapshot / run_store.RAW_LOG_NAME).write_bytes(b"\x1f\x8b")
        text = _text(snapshot / "run")
        assert "Plane 2:\n" not in text, text[-600:]

    def test_the_export_uses_the_same_sentence(self, snapshot):
        """`UX-314`'s attached report told the reader "no raw Plane 2
        log" for a run that never captured the plane at all."""
        page = payloads(str(snapshot / "run"))["report.json"]
        assert page.get("plane2_absence") == plane2.CAPTURED_NO_RAW_LOG
