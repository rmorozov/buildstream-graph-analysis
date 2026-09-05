"""UX-555: `with_trace=False` told a two-plane run it kept no Plane 2 log.

`export()`'s no-timeline fallback read `plane2.absence(run) or "this run
kept no raw Plane 2 log…"`. For a complete two-plane run exported with
`with_trace=False`, `absence()` is `None` — there is no absence — and the
`or` swallowed it into a sentence that is false: the log is right there,
and the reason for no timeline is that the caller asked for none.

Three states share the one key `timeline_omitted`, and each owes its own
reason:

* the caller asked for no trace — `with_trace=False`;
* the run has no Plane 2 to draw — `bga/plane2.py`'s absences;
* the timeline was rendered and refused for its size — `UX-530`'s ladder.

The discrimination *is* the guard, so all three are exported and read,
and the three sentences are asserted pairwise distinct. Swapping any two
in the module reddens: a one-sided guard that only checked "some sentence
is published" is exactly what let this survive `UX-545`, which fixed the
refusal branch one line over.

The fixture for the first state has to *have* a raw Plane 2 log or the
guard is vacuous, so it is asserted rather than assumed — the task file's
own Acceptance Test named `tests/fixtures/with_timeline`, which has no
Plane 2 at all (`absence()` there is `NOT_CAPTURED`).
"""
import json
import pathlib
import re
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import plane2, run_store
from tests import pages
from tools import bga_view

#: A run with no Plane 2 beside it at all - the second state.
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"


def _omitted(run, tmp_path, name, **kwargs):
    """`timeline_omitted` as the exported page actually publishes it."""
    out = tmp_path / f"{name}.html"
    bga_view.export(str(run), str(out), **kwargs)
    block = re.search(r'id="bga-run">(.*?)</script>',
                      out.read_text(encoding="utf-8"), re.S)
    return json.loads(block.group(1)).get("timeline_omitted")


@pytest.fixture
def complete(tmp_path):
    """A run whose Plane 2 is complete: report *and* raw log beside it.

    This is the state `absence()` has no sentence for, which is why the
    `or` reached the false one.
    """
    run = pages.two_plane_snapshot(tmp_path / "store")
    shutil.copy(REPO / "tests/fixtures/macro_micro/plane2.json",
                run.parent / run_store.PLANE2_NAME)
    assert run_store.sibling_raw_log(str(run)) is not None, (
        "the fixture has no raw Plane 2 log, so the sentence under test "
        "would be true and this guard would assert nothing")
    assert plane2.absence(str(run)) is None, (
        "the fixture has an absence, so the `or` never reaches its "
        "right-hand side and the defect is not being reproduced")
    return run


class TestEachReasonIsItsOwn:

    def test_the_flag_is_named_not_the_run(self, complete, tmp_path):
        """The acceptance test: a run that demonstrably kept its log is
        not told it kept none."""
        said = _omitted(complete, tmp_path, "declined", with_trace=False)
        assert said, "no reason published at all for an export that has none"
        assert "with_trace" in said, (
            f"the reason for no timeline is the caller's flag and the "
            f"sentence does not name it: {said!r}")
        assert "kept no raw Plane 2 log" not in said, (
            f"a run holding a raw Plane 2 log is told it kept none - the "
            f"defect UX-555 was filed on: {said!r}")

    def test_a_run_without_plane_two_gets_the_absence(self, tmp_path):
        """The second state keeps `bga/plane2.py`'s sentence - the same
        one the terminal prints, which `UX-329` exists to keep single."""
        said = _omitted(GOLDEN, tmp_path, "absent")
        assert said == plane2.NOT_CAPTURED, (
            f"a run that never captured Plane 2 no longer gets the "
            f"absence grammar's own sentence: {said!r}")

    def test_a_refusal_says_it_was_refused(self, complete, tmp_path,
                                           monkeypatch):
        """The third state, `UX-545`'s, still names its numbers. The
        ceiling is lowered rather than the fixture grown - `UX-430`
        measured where it belongs."""
        monkeypatch.setattr(bga_view, "TRACE_TRACK_BUDGET", 1)
        said = _omitted(complete, tmp_path, "refused")
        assert said and "ceiling" in said, (
            f"a timeline refused for its size does not say so: {said!r}")
        assert "with_trace" not in said, (
            f"a refusal blames the caller's flag, which was not passed: "
            f"{said!r}")

    def test_the_three_are_three_different_sentences(self, complete,
                                                     tmp_path, monkeypatch):
        """Collapsing two of them is the mutation this file exists for,
        and a clause that only checked "a sentence is published" would
        not see it."""
        declined = _omitted(complete, tmp_path, "d", with_trace=False)
        absent = _omitted(GOLDEN, tmp_path, "a")
        monkeypatch.setattr(bga_view, "TRACE_TRACK_BUDGET", 1)
        refused = _omitted(complete, tmp_path, "r")
        said = [declined, absent, refused]
        assert all(said), f"one of the three states published nothing: {said}"
        assert len(set(said)) == 3, (
            f"two of the three reasons for no timeline are the same "
            f"sentence, which is the defect UX-555 was filed for: {said}")
