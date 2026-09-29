"""`UX-1108`: a newer push to a pull request cancels its older run; a
push to main is never queued, replaced or cancelled.

The workflow's `concurrency:` is evaluated, not grepped, with
`test_a_run_red_for_another_reason_adopts_nothing`'s expression engine.
"""
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_a_run_red_for_another_reason_adopts_nothing import WORKFLOW, _Expr, _render

PR = {"event_name": "pull_request", "ref": "refs/pull/7/merge"}
PUSH = {"event_name": "push", "ref": "refs/heads/main"}


def _concurrency():
    block = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8")).get("concurrency")
    assert isinstance(block, dict), f"ci.yml has no top-level concurrency block: {block!r}"
    return block


def _group(github, run_id):
    return _render(str(_concurrency()["group"]), {"github": {**github, "run_id": run_id}})


def _cancels(github):
    value = _concurrency().get("cancel-in-progress", False)
    if isinstance(value, bool):
        return value
    return bool(_Expr(str(value), {"github": github}, {}).value())


def test_two_runs_of_one_pull_request_share_a_group():
    assert _group(PR, "101") == _group(PR, "102")


def test_two_pull_requests_do_not_share_a_group():
    other = {**PR, "ref": "refs/pull/8/merge"}
    assert _group(PR, "101") != _group(other, "101")


def test_two_pushes_to_main_never_share_a_group():
    """One group per run id: a third push cannot replace a pending second."""
    assert _group(PUSH, "101") != _group(PUSH, "102")


def test_the_group_is_prefixed_for_this_workflow():
    """Group names are repository-wide; another workflow's must not match."""
    assert _group(PR, "101").startswith("ci-"), _group(PR, "101")


def test_cancellation_holds_on_a_pull_request_only():
    assert _cancels(PR) is True
    assert _cancels(PUSH) is False
