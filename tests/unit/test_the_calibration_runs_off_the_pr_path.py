"""`UX-1110`: the width calibration gates nothing, so a pull request runs
it only under the `jobserver` label; a push to main always does.

The step's `if:` is evaluated with the replay engine of
`test_a_run_red_for_another_reason_adopts_nothing`.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_a_run_red_for_another_reason_adopts_nothing import _holds, _jobs, _status

#: Exact: `test_the_runners_width_is_calibrated.py` slices the step by it.
STEP = "Calibrate the runner's width and run the pinned 2x2 arm (UX-1004)"


def _step():
    found = [s for s in _jobs()["bst-examples"]["steps"] if s.get("name") == STEP]
    assert len(found) == 1, f"{len(found)} steps named {STEP!r} in bst-examples"
    return found[0]


def _pr(*labels):
    return {"event_name": "pull_request", "ref": "refs/pull/7/merge",
            "event": {"pull_request": {"labels": [{"name": n} for n in labels]}}}


PUSH = {"event_name": "push", "ref": "refs/heads/main", "event": {}}


@pytest.mark.parametrize("github, runs", [
    pytest.param(_pr(), False, id="pr-without-a-label"),
    pytest.param(_pr("documentation"), False, id="pr-with-another-label"),
    pytest.param(_pr("documentation", "jobserver"), True, id="pr-with-jobserver"),
    pytest.param(PUSH, True, id="push-to-main"),
])
def test_the_calibration_runs_where_it_is_read(github, runs):
    condition = _step().get("if")
    assert _holds(condition, {"github": github}, _status(["success"])) is runs, (
        github["event_name"], condition)
