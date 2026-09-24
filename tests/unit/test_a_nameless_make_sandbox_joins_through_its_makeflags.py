"""UX-1003: under fdsdk's `build-root: /buildstream-build` the shim cannot
name the element, so its kind reads `None`; an autotools sandbox still
carries BuildStream's own `MAKEFLAGS=-j4`, which promises a make recipe."""
import pytest

from tests.unit.test_bwrap_shim import REAL_BWRAP_ARGV, _decide_through_the_real_gate
from tools.native_trace.bwrap_shim import kind_job_env, recipe_promise

AUTH = "--jobserver-auth=fifo:/tmp/.bst-native-trace/jobserver"


def _argv(**setenv):
    argv = list(REAL_BWRAP_ARGV)
    at = argv.index("JOBS") - 1
    del argv[at:at + 3]
    argv[argv.index("--dir") + 1] = "buildstream-build"
    for name, value in setenv.items():
        argv[at:at] = ["--setenv", name, value]
    return argv


@pytest.mark.parametrize(("setenv", "promise"), [
    ({"MAKEFLAGS": "-j4"}, "MAKEFLAGS"), ({"MAKEFLAGS": "-k -j 8"}, "MAKEFLAGS"),
    ({"MAKEFLAGS": "-k"}, None), ({}, None),
    ({"JOBS": "-j4", "MAKEFLAGS": "-j4"}, "JOBS")])
def test_the_promise_is_read_off_buildstreams_own_setenv(setenv, promise):
    assert recipe_promise(_argv(**setenv)) == promise


def test_a_makeflags_promise_joins_as_make():
    pairs, unsets, policy = kind_job_env(None, AUTH, jobs_present="MAKEFLAGS")
    assert (pairs, unsets, policy) == ([("MAKEFLAGS", AUTH)], [], "make")


def test_the_real_gate_records_make_for_fdsdks_autotools_shape(tmp_path, monkeypatch):
    policy, _marker = _decide_through_the_real_gate(
        tmp_path, monkeypatch, None, _argv(MAKEFLAGS="-j4"), "exit 127\n")
    assert policy == "make"


def test_a_sandbox_with_no_promise_stays_unknown(tmp_path, monkeypatch):
    policy, _marker = _decide_through_the_real_gate(
        tmp_path, monkeypatch, None, _argv(), "exit 127\n")
    assert policy == "unknown_kind"
