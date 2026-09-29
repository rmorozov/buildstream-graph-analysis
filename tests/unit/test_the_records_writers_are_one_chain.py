"""`UX-1091`: no records writer can cancel another.

`concurrency: records` keeps one job running and one pending per group;
a newer arrival cancels the pending one (`#297`, `39d89d47`:
`flake-ledger-adopt` pended and `touch-map-adopt` cancelled it). This
file reads `ci.yml` for the fix: every job running `dev_records.py
publish` is totally ordered by the transitive `needs` closure, so at
most one is ever pending, and a writer needing a writer still runs past
a skipped one (`!cancelled()` or `always()`).
"""

import pathlib

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/ci.yml"
PUBLISH = "dev_records.py publish"


def _jobs():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]


def _writers():
    jobs = _jobs()
    found = {}
    for name, job in jobs.items():
        for step in job.get("steps") or []:
            if PUBLISH in (step.get("run") or ""):
                found[name] = job
    return found


def _needs(job):
    needs = job.get("needs") or []
    return [needs] if isinstance(needs, str) else list(needs)


def _ancestors(name, jobs, seen=None):
    """The transitive `needs` closure of `name`."""
    seen = seen if seen is not None else set()
    for parent in _needs(jobs[name]):
        if parent not in seen:
            seen.add(parent)
            _ancestors(parent, jobs, seen)
    return seen


def test_the_workflow_has_the_four_writers():
    """A parse that found nothing would pass every check below."""
    assert len(_writers()) == 4, sorted(_writers())


def test_every_writer_is_ordered_after_every_other_writer():
    """Totally ordered by `needs`: for any two writers, one is an
    ancestor of the other - otherwise both could be pending together."""
    writers = _writers()
    jobs = _jobs()
    names = sorted(writers)
    for i, a in enumerate(names):
        ancestors_a = _ancestors(a, jobs)
        for b in names[i + 1 :]:
            ancestors_b = _ancestors(b, jobs)
            assert b in ancestors_a or a in ancestors_b, (a, b)


def test_a_writer_needing_a_writer_runs_past_a_skip():
    """`needs: [test, touch-map-adopt]` alone would block on a skipped
    `touch-map-adopt`; the job's `if` must carry `!cancelled()` or
    `always()` so a skip upstream does not stall the chain."""
    writers = _writers()
    for name, job in sorted(writers.items()):
        writer_parents = [p for p in _needs(job) if p in writers]
        if not writer_parents:
            continue
        condition = job.get("if") or ""
        assert "!cancelled()" in condition or "always()" in condition, (name, condition)


def test_every_writer_shares_the_records_concurrency_group():
    for name, job in sorted(_writers().items()):
        assert job.get("concurrency") == "records", name
