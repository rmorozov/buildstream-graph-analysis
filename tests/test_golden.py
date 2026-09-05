"""P3-08: golden/regression test.

Runs the full pipeline (via the real CLI, subprocess - the same
end-to-end path a user actually invokes) against a checked-in fixture
and diffs the output against a checked-in expected snapshot, exactly.
No tolerance of any kind: the pipeline is fully deterministic (Part 35/
I11, see tests/unit/test_determinism.py), so any diff here is either a
genuine behavior change (update the snapshot deliberately, see below)
or a real regression.

This is a coarse safety net on top of the targeted unit/invariant tests
(P3-03 through P3-07) - it catches unintended drift in *any* output
field, but doesn't explain *why* something changed. Don't add new
correctness assertions here; add them to the targeted test files instead.

## Regenerating the expected output after a deliberate behavior change

    python3 tools/dev_refresh_analysis.py --write \\
        tests/fixtures/golden/mixed_task_kinds

Then confirm the diff you expected is the only change
(`git diff tests/fixtures/golden/mixed_task_kinds/expected_output.json`).

`UX-486`: that command **is** what this file compares against, because
both call `dev_refresh_analysis.Fixture.analysed`. The recipe used to
be a shell pipeline in this docstring and a Python function below it,
and the second committed analysis in the tree - `with_timeline` - had
neither and drifted four findings behind the analyzer. Which keys are
the machine rather than the analysis, and why each is dropped, is
stated once in that tool.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tools import dev_refresh_analysis as refresh


def _fixture():
    """The golden's entry in the one list of committed analyses.

    Looked up rather than constructed, so a fixture this file compares
    and the tool cannot regenerate is impossible - which is the state
    `with_timeline` was in for four rounds.
    """
    for fixture in refresh.FIXTURES:
        if fixture.name.endswith("golden/mixed_task_kinds"):
            return fixture
    raise AssertionError(
        "the golden fixture is not in dev_refresh_analysis.FIXTURES, so "
        "nothing can regenerate what this file compares against")


def test_mixed_task_kinds_golden_snapshot():
    fixture = _fixture()
    assert fixture.analysed() == fixture.committed()


def test_mixed_task_kinds_golden_snapshot_is_deterministic_across_runs():
    """Two independent CLI invocations against the same fixture must
    produce byte-identical output (Part 35/I11) - a weaker but
    complementary check to the fixed-snapshot comparison above, since it
    can't be fooled by an expected_output.json that was itself captured
    from a nondeterministic run."""
    fixture = _fixture()
    assert fixture.analysed() == fixture.analysed()
