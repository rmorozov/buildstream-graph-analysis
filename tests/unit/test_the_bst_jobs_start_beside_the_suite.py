"""`UX-1109`: the bst jobs read nothing `test` produces, so none of them
waits for it - not directly, and not through another job's `needs`."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_the_records_writers_are_one_chain import _ancestors, _jobs, _needs

BST_JOBS = ("bst-smoke", "bst-tests", "bst-examples")


def test_the_workflow_has_the_bst_jobs_and_the_suite():
    """A parse that found none of them would pass the check below."""
    jobs = _jobs()
    assert "test" in jobs
    assert all(name in jobs for name in BST_JOBS), sorted(jobs)


@pytest.mark.parametrize("name", BST_JOBS)
def test_no_bst_job_waits_for_the_suite(name):
    ancestors = _ancestors(name, _jobs())
    assert "test" not in ancestors, (name, sorted(ancestors))


@pytest.mark.parametrize("name", BST_JOBS)
def test_every_bst_job_still_skips_on_a_docs_only_diff(name):
    """Dropping `test` must not drop the `changes` gate it came with; the
    `needs` context holds direct needs only, so `changes` must be one."""
    job = _jobs()[name]
    assert "changes" in _needs(job), (name, _needs(job))
    assert "needs.changes.outputs.docs_only != 'true'" in job["if"], job["if"]
