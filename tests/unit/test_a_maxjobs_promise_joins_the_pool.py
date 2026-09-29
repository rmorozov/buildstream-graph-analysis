"""UX-1007: a bare-integer `MAXJOBS`/`MAX_JOBS` promises a width, so a sandbox
with no nameable kind joins as `maxjobs_env`; project-wide `GOMAXPROCS` and
`CARGO_BUILD_JOBS` promise nothing."""

import pytest

from tests.unit.test_a_nameless_make_sandbox_joins_through_its_makeflags import AUTH, _argv
from tests.unit.test_bwrap_shim import _decide_through_the_real_gate
from tools.native_trace.bwrap_shim import (
    JOBSERVER_PINNED,
    jobserver_decision,
    kind_job_env,
    parse_element_max_jobs,
    recipe_promise,
)


@pytest.mark.parametrize("name", ["MAXJOBS", "MAX_JOBS"])
def test_a_maxjobs_promise_gets_the_auth_and_its_own_policy(name, tmp_path, monkeypatch):
    opts = _argv(**{name: "4"})
    assert recipe_promise(opts) == "MAXJOBS"
    pairs, unsets, policy = kind_job_env(None, AUTH, jobs_present=recipe_promise(opts))
    assert (pairs, unsets, policy) == ([("MAKEFLAGS", AUTH)], [], "maxjobs_env")
    got, _marker = _decide_through_the_real_gate(tmp_path, monkeypatch, None, opts, "exit 127\n")
    assert got == "maxjobs_env"


def test_only_project_wide_variables_still_read_unknown_kind(tmp_path, monkeypatch):
    opts = _argv(GOMAXPROCS="4", CARGO_BUILD_JOBS="4")
    assert recipe_promise(opts) is None
    got, _marker = _decide_through_the_real_gate(tmp_path, monkeypatch, None, opts, "exit 127\n")
    assert got == "unknown_kind"


def test_a_maxjobs_of_one_is_pinned():
    opts = _argv(MAXJOBS="1")
    assert jobserver_decision(parse_element_max_jobs(opts), None) == JOBSERVER_PINNED
