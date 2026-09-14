"""UX-851: the jobserver is a capture option and a snapshot fact.

`--jobserver N` (`UX-679`) and `jobserver_auth` (`UX-841`) are a tracer
flag and a report field; nothing between the CLI and the page knew the
mode, so two captures of one project could not be told apart by it.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURE_RUN = REPO / "tests/fixtures/with_timeline/run"

from bga.cli import _translate_capture_jobserver, resolve_jobserver_ceiling
from bga.compare import ComparisonResult
from bga.report.text import format_compare_text
from tools.bst_extract_run import _read_bga_jobserver_env, extract_run
from tools.bst_native_build_tracer import _jobserver_block

from ._bst_env import bst_env, isolated_bst_env
from .test_bst_extract_run import BST_AVAILABLE, BST_SKIP_REASON, FIXTURE_PROJECT


@pytest.fixture(autouse=True)
def _no_stray_jobserver_mode():
    """`_translate_capture_jobserver` sets `os.environ` directly (not
    through `monkeypatch`), since it has to survive into the same
    process's later call to the tracer's `main()` - so this file cleans
    up after itself rather than leaking the variable into whatever test
    the suite runs next."""
    had = os.environ.pop('BGA_JOBSERVER_MODE', None)
    yield
    if had is None:
        os.environ.pop('BGA_JOBSERVER_MODE', None)
    else:
        os.environ['BGA_JOBSERVER_MODE'] = had


class TestTheCLIParsesTheThreeModes:
    def test_off_passes_nothing(self):
        assert resolve_jobserver_ceiling('off', []) == ('off', None)

    def test_an_explicit_n_passes_through(self):
        assert resolve_jobserver_ceiling('4', []) == ('n', 4)

    def test_auto_sizes_to_cores_minus_builders(self):
        wrapped = ['bst', 'build', '--builders', '3', 'all.bst']
        assert resolve_jobserver_ceiling('auto', wrapped, cpu_count=8) == ('auto', 5)

    def test_auto_with_no_named_builders_reserves_one_core(self):
        assert resolve_jobserver_ceiling('auto', ['bst', 'build'], cpu_count=8) == ('auto', 7)

    def test_auto_floors_at_one(self):
        wrapped = ['bst', 'build', '--builders', '30']
        assert resolve_jobserver_ceiling('auto', wrapped, cpu_count=8) == ('auto', 1)

    def test_an_unrecognised_value_resolves_to_nothing(self):
        assert resolve_jobserver_ceiling('bogus', []) == (None, None)

    def test_zero_tokens_is_off_and_a_negative_is_passed_through(self):
        assert resolve_jobserver_ceiling('0', []) == ('off', None)
        assert resolve_jobserver_ceiling('-3', []) == (None, None)

    def test_a_later_call_without_the_flag_resets_the_variable(self, monkeypatch):
        monkeypatch.delenv('BGA_JOBSERVER_MODE', raising=False)
        _translate_capture_jobserver(['capture', 'run', 'proj', 'out.json',
                                      '--jobserver', '4', '--', 'bst', 'build'])
        assert os.environ['BGA_JOBSERVER_MODE'] == 'n'
        _translate_capture_jobserver(['capture', 'run', 'proj', 'out.json',
                                      '--', 'bst', 'build'])
        assert os.environ['BGA_JOBSERVER_MODE'] == 'off'

    def test_the_argv_translates_auto_into_the_tracers_own_int_flag(self, monkeypatch):
        monkeypatch.delenv('BGA_JOBSERVER_MODE', raising=False)
        argv = ['capture', 'run', 'proj', 'out.json', '--jobserver', 'auto',
                '--', 'bst', 'build', '--builders', '3']
        translated = _translate_capture_jobserver(argv)
        assert '--jobserver' in translated
        i = translated.index('--jobserver')
        assert translated[i + 1].isdigit()
        assert translated[-4:] == ['--', 'bst', 'build', '--builders', '3'][-4:] \
            or translated[-4:] == ['bst', 'build', '--builders', '3']

    def test_off_drops_the_flag_entirely(self, monkeypatch):
        monkeypatch.delenv('BGA_JOBSERVER_MODE', raising=False)
        argv = ['capture', 'run', 'proj', 'out.json', '--jobserver', 'off',
                '--', 'bst', 'build']
        translated = _translate_capture_jobserver(argv)
        assert '--jobserver' not in translated

    def test_a_command_that_is_not_capture_run_is_untouched(self):
        argv = ['analyze', 'run', '--jobserver', 'auto']
        assert _translate_capture_jobserver(argv) == argv


class TestTheSnapshotFactReachesAnalyzeJSON:
    """`copy tests/fixtures/with_timeline/run and add the report fields;
    skip the live capture` - `run-context.json` gains the block a real
    capture would eventually write, and `bga analyze` publishes it
    unmodified under `run_instance.jobserver`."""

    def _run(self, tmp_path, jobserver_block=None):
        target = tmp_path / "run"
        shutil.copytree(FIXTURE_RUN, target)
        if jobserver_block is not None:
            ctx_path = target / "run-context.json"
            ctx = json.loads(ctx_path.read_text())
            ctx["jobserver"] = jobserver_block
            ctx_path.write_text(json.dumps(ctx))
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", str(target),
             "--format", "json"],
            capture_output=True, text=True, cwd=REPO, timeout=120)
        assert done.returncode == 0, done.stderr
        return json.loads(done.stdout)

    def test_a_capture_report_s_jobserver_fields_land_under_run_instance(self, tmp_path):
        # `jobserver: 4` and `jobserver_auth: fd` are the tracer report's
        # own field names (`UX-679`, `UX-841`); `ceiling`/`auth` here are
        # exactly those two values, in the shape `run_instance` publishes.
        block = {"mode": "n", "ceiling": 4, "auth": "fd", "project_max_jobs": None}
        data = self._run(tmp_path, block)
        assert data["run_instance"]["jobserver"] == block

    def test_an_old_snapshot_carries_no_jobserver_key_at_all(self, tmp_path):
        data = self._run(tmp_path, jobserver_block=None)
        assert "jobserver" not in data["run_instance"]


class TestCompareNamesTheModeInItsHeader:
    def _comparison(self, baseline_job, candidate_job):
        return ComparisonResult(
            baseline_run_id='a' * 8, candidate_run_id='b' * 8,
            baseline_metrics={'total_duration_us': 10_000_000},
            candidate_metrics={'total_duration_us': 9_000_000},
            deltas={'total_duration_us': -1_000_000},
            baseline_confidence=1.0, candidate_confidence=1.0,
            attribution_deltas={}, verdict='IMPROVED', low_confidence=False,
            baseline_run_instance={'jobserver': baseline_job} if baseline_job else {},
            candidate_run_instance={'jobserver': candidate_job} if candidate_job else {},
        )

    def test_an_old_snapshot_reads_as_off(self):
        text = format_compare_text(self._comparison(None, None))
        assert text.count("jobserver off") == 2

    def test_both_modes_print(self):
        comparison = self._comparison(
            None, {"mode": "auto", "ceiling": 7, "auth": "fd", "project_max_jobs": None})
        text = format_compare_text(comparison)
        assert "jobserver off" in text
        assert "jobserver auto (ceiling 7)" in text


class TestExtractionValidatesTheJobserverEnvNames:
    def _project(self, tmp_path, declaration):
        project = tmp_path / "proj"
        (project / "elements").mkdir(parents=True)
        variables = f"variables:\n  bga-jobserver-env: {declaration}\n" if declaration else ""
        (project / "project.conf").write_text(
            f"name: p\nmin-version: 2.0\nelement-path: elements\n{variables}")
        return project

    def test_absent_is_an_empty_list(self, tmp_path):
        project = self._project(tmp_path, None)
        assert _read_bga_jobserver_env(str(project)) == []

    def test_a_well_shaped_entry_is_accepted(self, tmp_path):
        project = self._project(tmp_path, "MYJOBS=-j")
        assert _read_bga_jobserver_env(str(project)) == [
            {"name": "MYJOBS", "prefix": "-j"}]

    def test_a_bare_name_with_no_prefix_is_rejected_by_name(self, tmp_path):
        project = self._project(tmp_path, "MYJOBS")
        with pytest.raises(RuntimeError, match="MYJOBS"):
            _read_bga_jobserver_env(str(project))

    def test_a_name_starting_with_a_digit_is_rejected_by_name(self, tmp_path):
        project = self._project(tmp_path, "9X=-j")
        with pytest.raises(RuntimeError, match="9X=-j"):
            _read_bga_jobserver_env(str(project))


class TestTheTracerAssemblesTheBlockFromItsReportAndTheEnvironment:
    """`bga capture` sets `BGA_JOBSERVER_MODE` beside the `--jobserver N`
    it already resolves (in-process, since `dispatch()` calls the
    tracer's `main()` directly) - the tracer needs no CLI parsing of its
    own to recover the mode."""

    def test_a_resolved_capture_carries_every_field(self, monkeypatch):
        monkeypatch.setenv('BGA_JOBSERVER_MODE', 'n')
        report = {'jobserver': 4, 'jobserver_auth': 'fd', 'project_max_jobs': 8}
        assert _jobserver_block(report) == {
            'mode': 'n', 'ceiling': 4, 'auth': 'fd', 'project_max_jobs': 8}

    def test_no_jobserver_and_no_variable_reads_off(self, monkeypatch):
        monkeypatch.delenv('BGA_JOBSERVER_MODE', raising=False)
        assert _jobserver_block({}) == {
            'mode': 'off', 'ceiling': None, 'auth': None, 'project_max_jobs': None}

    def test_the_translate_step_sets_the_variable_for_auto(self, monkeypatch):
        monkeypatch.delenv('BGA_JOBSERVER_MODE', raising=False)
        argv = ['capture', 'run', 'proj', 'out.json', '--jobserver', 'auto',
                '--', 'bst', 'build']
        _translate_capture_jobserver(argv)
        assert os.environ['BGA_JOBSERVER_MODE'] == 'auto'


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason=BST_SKIP_REASON)
class TestExtractionWritesTheJobserverBlockToRunContext:
    """The tracer does not write `run-context.json` itself - it
    delegates to `tools/bst_extract_run.py::extract_run`, which is where
    this block actually lands on disk (found by reading the `run`
    command's own `extract_run(...)` call site)."""

    def _extracted(self, tmp_path, jobserver):
        log_path = tmp_path / "real_build.log"
        proc = subprocess.run(
            ["bst", "-C", str(FIXTURE_PROJECT), "--no-colors", "build", "app.bst"],
            capture_output=True, text=True, env=isolated_bst_env(tmp_path))
        log_path.write_text(proc.stdout + proc.stderr)
        out_dir = tmp_path / "run"
        with bst_env(tmp_path):
            extract_run(str(FIXTURE_PROJECT), str(log_path), str(out_dir),
                        log_format="auto", jobserver=jobserver)
        return json.loads((out_dir / "run-context.json").read_text())

    def test_the_block_lands_with_the_values_given(self, tmp_path):
        block = {"mode": "n", "ceiling": 4, "auth": "fd", "project_max_jobs": None}
        run_context = self._extracted(tmp_path, block)
        assert run_context["jobserver"] == block

    def test_a_capture_with_no_jobserver_writes_off(self, tmp_path):
        block = _jobserver_block({})
        run_context = self._extracted(tmp_path, block)
        assert run_context["jobserver"] == {
            "mode": "off", "ceiling": None, "auth": None, "project_max_jobs": None}
