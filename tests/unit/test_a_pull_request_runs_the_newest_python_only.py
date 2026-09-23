"""`UX-995`: a pull request queues behind another's matrix - the owner
chose the newest Python for it alone; a push still runs all four.

Reuses `test_a_run_red_for_another_reason_adopts_nothing`'s replay
engine (`_jobs`, `_Expr`, `_holds`, `_status`, `_matrix_cells`) rather
than a second parser for the same expression language.
"""
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_a_run_red_for_another_reason_adopts_nothing import (
    _holds,
    _jobs,
    _matrix_cells,
    _status,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
PYPROJECT = REPO / "pyproject.toml"
MAKE_TEST = re.compile(r"\bmake test(?!-)")


def _version_key(version):
    return tuple(int(part) for part in version.split("."))


def _classifiers():
    """pyproject.toml's own `Programming Language :: Python :: X.Y` rows."""
    text = PYPROJECT.read_text(encoding="utf-8")
    found = re.findall(r'Programming Language :: Python :: (\d+\.\d+)"', text)
    assert found, "pyproject.toml declares no Python version classifiers"
    return sorted(found, key=_version_key)


def _is_make_test_variant(step):
    return bool(MAKE_TEST.search(step.get("run") or ""))


def _pr_context(version):
    return {"matrix": {"python-version": version},
            "github": {"event_name": "pull_request", "ref": "refs/pull/1/merge",
                       "event": {"repository": {"default_branch": "main"}}}}


def _push_context(version):
    return {"matrix": {"python-version": version},
            "github": {"event_name": "push", "ref": "refs/heads/main",
                       "event": {"repository": {"default_branch": "main"}}}}


#: `UX-995`: deliberately push-only. Named, not matched by a substring
#: on `github.event_name == 'push'` - a mutation could paste that same
#: substring onto any other step and a substring check would exempt it
#: too, silently dropping it from every pull request (round 139
#: verifier hold).
PUSH_ONLY_STEPS = (
    "Test (with a coverage-derived touching map)",
    "This run's touching map, for adopting",
    "Upload it, so the adopt job can merge it",
)


def test_the_push_matrix_equals_pyprojects_classifiers():
    jobs = _jobs()
    push = sorted(_matrix_cells(jobs, {"event_name": "push"}), key=_version_key)
    assert push == _classifiers(), (
        f"push runs {push}, pyproject.toml declares {_classifiers()} - a "
        f"pull request's own cell must stay one of the classifiers")


def test_the_pull_request_matrix_is_the_newest_classifier_alone():
    jobs = _jobs()
    push = _matrix_cells(jobs, {"event_name": "push"})
    pr = _matrix_cells(jobs, {"event_name": "pull_request"})
    assert pr == [max(push, key=_version_key)], (
        f"pull_request runs {pr}, not the newest of {push} alone")


def test_exactly_one_make_test_step_holds_per_event_and_cell():
    """Neither event may leave a cell with no suite run, nor two -
    two would be two references for `UX-420`'s one-reference rule."""
    jobs = _jobs()
    variants = [s for s in jobs["test"]["steps"] if _is_make_test_variant(s)]
    for event in ("push", "pull_request"):
        for version in _matrix_cells(jobs, {"event_name": event}):
            context = {"matrix": {"python-version": version},
                       "github": {"event_name": event}}
            holding = [s["name"] for s in variants
                       if _holds(s.get("if"), context, _status(["success"]))]
            assert len(holding) == 1, (event, version, holding)


def test_every_pull_request_step_moves_to_the_cell_it_keeps():
    """The Required Fix's own words: a step a pull request needed from a
    cell it no longer gets moves to the cell it keeps. "Needed" is read
    off the real push matrix - the closest thing left to the uniform
    matrix a pull request once shared - so a step rebound to a retired
    cell (the drift gate's old '3.11') reds here even though no live PR
    ever reaches that `if:`.

    Exemption is `PUSH_ONLY_STEPS`, by name - not a substring on the
    step's own `if:`, which a mutation could copy onto any other step
    and exempt it too (round 139 verifier hold: `&& github.event_name
    == 'push'` pasted onto the 3.12 perf-carry restore stayed green
    under the substring version).

    `make test` steps are `test_exactly_one_..._per_event_and_cell`'s
    job, not this one's - three steps deliberately share one cell.
    """
    jobs = _jobs()
    push = _matrix_cells(jobs, {"event_name": "push"})
    newest = max(push, key=_version_key)
    for step in jobs["test"]["steps"]:
        if _is_make_test_variant(step) or step.get("name") in PUSH_ONLY_STEPS:
            continue
        condition = step.get("if")
        held_on_push = any(_holds(condition, _push_context(v), _status(["success"]))
                           for v in push)
        if not held_on_push:
            continue
        assert _holds(condition, _pr_context(newest), _status(["success"])), (
            f"{step.get('name')!r} holds on some push cell but not on "
            f"(pull_request, {newest!r}), and it is not in PUSH_ONLY_STEPS")
