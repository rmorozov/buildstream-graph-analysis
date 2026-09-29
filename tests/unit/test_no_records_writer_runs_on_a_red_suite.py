"""`UX-1115`: no job that publishes to `records` runs on a push whose
suite failed - a skipped upstream writer satisfies `!cancelled()`, so
each writer downstream of `test` must name a success it can read.

Read two ways: the Decision's static clause per writer, and a replay of
every writer's `if:` in `needs` order with `test` red.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_a_run_red_for_another_reason_adopts_nothing import MAIN, _holds, _status
from test_the_records_writers_are_one_chain import _ancestors, _jobs, _needs, _writers

CLEAN = ("clean_39", "clean_310", "clean_311", "clean_312")


def _reads_a_success(job):
    """Some need on the `test` chain, read as a success or a clean cell."""
    condition = " ".join(str(job.get("if") or "").split())
    jobs = _jobs()
    chain = [j for j in _needs(job) if j == "test" or "test" in _ancestors(j, jobs)]
    return (any(f"needs.{j}.result == 'success'" in condition for j in chain)
            or "needs.test.outputs.clean_" in condition)


def test_every_writer_needs_the_suite():
    """A writer off the `test` chain would pass both checks below vacuously."""
    jobs = _jobs()
    for name in _writers():
        assert "test" in _ancestors(name, jobs), name


@pytest.mark.parametrize("name", sorted(_writers()))
def test_each_writer_names_a_success_on_the_suites_chain(name):
    job = _writers()[name]
    assert _reads_a_success(job), (name, job.get("if"))


def _replay(test_outputs, test_result="failure", forced=None):
    """Which writers run on a push to main; `forced` sets a writer's result."""
    jobs, writers, forced = _jobs(), _writers(), forced or {}
    order = sorted(writers, key=lambda n: len(_ancestors(n, jobs)))
    needs = {"test": {"result": test_result, "outputs": test_outputs}}
    ran = []
    for name in order:
        results = [needs[need]["result"] for need in _needs(jobs[name])]
        runs = _holds(jobs[name].get("if"), {"needs": needs, "github": MAIN},
                      _status(results))
        needs[name] = {"result": forced.get(name, "success" if runs else "skipped")}
        if runs:
            ran.append(name)
    return ran


def test_a_red_suite_publishes_nothing():
    assert _replay({}) == []


def test_a_run_red_at_the_drift_step_alone_appends_the_ledger_only():
    """`UX-943`: every cell clean but the drift step red - the ledger's
    rows are that step's excursions; nothing else publishes."""
    assert _replay(dict.fromkeys(CLEAN, "true")) == ["flake-ledger-adopt"]


def test_a_green_push_publishes_the_pages():
    """The control: a condition nothing satisfies passes both red cases."""
    ran = _replay(dict.fromkeys(CLEAN, "true"), test_result="success")
    assert "area-pages-publish" in ran, ran


def test_a_failed_ledger_append_publishes_no_pages():
    ran = _replay(dict.fromkeys(CLEAN, "true"), test_result="success",
                  forced={"flake-ledger-adopt": "failure"})
    assert "touch-map-adopt" in ran and "area-pages-publish" not in ran, ran
