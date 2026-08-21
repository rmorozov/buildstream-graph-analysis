"""UX-185: a capture that slept must know it slept.

Field feedback: *"there also can be scenario with computer going to
sleep during the capture — well known pattern on ubuntu is
`systemd-inhibit --what=sleep:shutdown gnome-session-inhibit --inhibit
idle ./my_long_script.sh` — maybe something like that can be embedded
into some command line switch."*

The reason this is worse than a slow build, ground-truthed in round 20:
the hook and the spine stamp `CLOCK_MONOTONIC` (`hook.c:324`,
`spine.c:198`), which does **not** advance while the machine is
suspended, and the Plane 1 wrapper stamps wall clock. So a suspend
mid-capture leaves Plane 2 under-reporting, Plane 1 over-reporting, and
nothing about the run looking wrong.

Suspend is **simulated**, not performed: the seam is the clock pair the
wrapper records, so a test injects a drift rather than closing a lid.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import suspend

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"


def _bga(args):
    return subprocess.run(
        [sys.executable, "-c",
         "from bga.cli import main; raise SystemExit(main(%r))" % (args,)],
        capture_output=True, text=True, cwd=os.getcwd())


def _slept_run(tmp_path, name, seconds):
    """A run directory whose capture recorded `seconds` of sleep."""
    run = tmp_path / name
    shutil.copytree(GOLDEN, run)
    os.remove(run / "expected_output.json")
    context = json.loads((run / "run-context.json").read_text())
    outcome = dict(context.get("build_outcome") or
                   {"failed_elements": [], "failed_count": 0, "interrupted": False})
    if seconds:
        outcome["suspended"] = {"suspended_seconds": seconds}
    context["build_outcome"] = outcome
    (run / "run-context.json").write_text(json.dumps(context, indent=2))
    return run


class TestTheTwoClocks:
    def test_no_drift_is_no_suspend(self):
        start = {"wall": 1000.0, "monotonic": 500.0}
        end = {"wall": 1900.0, "monotonic": 1400.0}
        assert suspend.slept(start, end) is None

    def test_wall_running_ahead_of_monotonic_is_a_suspend(self):
        """The signature: the machine was off for the difference."""
        start = {"wall": 1000.0, "monotonic": 500.0}
        end = {"wall": 4600.0, "monotonic": 1400.0}   # 3600s wall, 900s awake
        assert suspend.slept(start, end) == {"suspended_seconds": 2700.0}

    def test_a_small_drift_is_ntp_not_a_lid(self):
        """`adjtime` slews at up to 500ppm - 1.8s per hour of build - so
        the threshold has to sit above that and below the shortest
        suspend a lid can produce."""
        start = {"wall": 1000.0, "monotonic": 500.0}
        end = {"wall": 4602.0, "monotonic": 4100.0}   # 2s of slew over an hour
        assert suspend.slept(start, end) is None

    def test_a_backwards_wall_clock_step_is_not_a_suspend(self):
        """NTP can step time backwards. That is not sleep, and reporting
        it as sleep would refuse a perfectly good capture."""
        start = {"wall": 1000.0, "monotonic": 500.0}
        end = {"wall": 1300.0, "monotonic": 1400.0}
        assert suspend.slept(start, end) is None

    def test_a_capture_with_no_clock_pair_is_not_a_suspend(self):
        """Every log written before UX-185. A capture too old to have
        looked is not a capture that slept."""
        assert suspend.slept(None, {"wall": 1.0, "monotonic": 1.0}) is None
        assert suspend.slept({"wall": 1.0, "monotonic": 1.0}, None) is None


class TestTheWrapperRecordsThePair:
    def test_both_ends_reach_the_log(self, tmp_path):
        from tools.bst_run_wrapped import read_clock_pairs, run_wrapped

        bst = tmp_path / "bst"
        bst.write_text("#!/bin/sh\necho building\n")
        bst.chmod(0o755)
        log = tmp_path / "build.log"
        with open(log, "w", encoding="utf-8") as handle:
            run_wrapped(str(tmp_path), [str(bst)], handle)

        pairs = read_clock_pairs(str(log))
        assert set(pairs) == {"start", "end"}
        assert pairs["end"]["monotonic"] >= pairs["start"]["monotonic"]

    def test_the_invocation_line_still_records_the_real_command(self, tmp_path):
        """`UX-29` recovers `--max-jobs` from `Executing command:`. A
        clock line beside it must not become that line, and `--inhibit`
        must not rewrite it into `systemd-inhibit ... bst build`."""
        from tools.bst_run_wrapped import run_wrapped

        bst = tmp_path / "bst"
        bst.write_text("#!/bin/sh\nexit 0\n")
        bst.chmod(0o755)
        log = tmp_path / "build.log"
        with open(log, "w", encoding="utf-8") as handle:
            run_wrapped(str(tmp_path), [str(bst), "build", "--max-jobs", "4"],
                        handle, inhibit=True)

        executing = [line for line in log.read_text().splitlines()
                     if "Executing command:" in line]
        assert len(executing) == 1
        assert "--max-jobs 4" in executing[0]
        assert "systemd-inhibit" not in executing[0]

    def test_a_log_without_the_marker_yields_nothing(self, tmp_path):
        from tools.bst_run_wrapped import read_clock_pairs

        log = tmp_path / "old.log"
        log.write_text("[wrapper][2026-01-01 00:00:00,000] INFO: Return code: 0\n")
        assert read_clock_pairs(str(log)) == {}


class TestTheInhibitors:
    def test_both_layers_wrap_the_command_when_present(self, monkeypatch):
        monkeypatch.setattr(suspend, "available", lambda: {
            "systemd-inhibit": "/usr/bin/systemd-inhibit",
            "gnome-session-inhibit": "/usr/bin/gnome-session-inhibit",
        })
        argv = suspend.inhibit_argv(["bst", "build", "all.bst"])
        assert argv[:4] == ["/usr/bin/systemd-inhibit", "--what=sleep:shutdown",
                            "--why=bga capture", "--who=bga"]
        assert argv[4:7] == ["/usr/bin/gnome-session-inhibit", "--inhibit", "idle"]
        assert argv[-3:] == ["bst", "build", "all.bst"]

    def test_a_headless_machine_gets_the_half_that_applies(self, monkeypatch):
        monkeypatch.setattr(suspend, "available", lambda: {
            "systemd-inhibit": "/usr/bin/systemd-inhibit",
            "gnome-session-inhibit": None,
        })
        argv = suspend.inhibit_argv(["bst", "build"])
        assert "gnome-session-inhibit" not in " ".join(argv)
        assert argv[0] == "/usr/bin/systemd-inhibit"

    def test_a_machine_with_neither_says_so_and_runs_anyway(self, monkeypatch):
        monkeypatch.setattr(suspend, "available", lambda: {
            "systemd-inhibit": None, "gnome-session-inhibit": None})
        assert suspend.inhibit_argv(["bst", "build"]) == ["bst", "build"]
        notice = suspend.unavailable_notice()
        assert notice and "Running anyway" in notice
        assert "detected either way" in notice

    def test_no_notice_when_an_inhibitor_exists(self, monkeypatch):
        monkeypatch.setattr(suspend, "available", lambda: {
            "systemd-inhibit": "/usr/bin/systemd-inhibit",
            "gnome-session-inhibit": None})
        assert suspend.unavailable_notice() is None

    def test_the_flag_is_on_both_capture_commands(self):
        for command in (["snapshot", "--help"], ["capture", "run", "--help"]):
            result = _bga(command)
            assert "--inhibit" in result.stdout, command


class TestTheRunSaysItSlept:
    def test_the_run_context_reports_the_suspension(self, tmp_path):
        from bga.ingest.loader import load_run_context

        run = _slept_run(tmp_path, "slept", 2700.0)
        context = load_run_context(str(run / "run-context.json"))
        assert context.suspension == {"suspended_seconds": 2700.0}
        assert context.incomplete_reason == "suspended", (
            "UX-156's grammar is what makes analyze banner it and compare "
            "refuse - a third reason must feed the same accessor")

    def test_a_normal_run_is_still_complete(self, tmp_path):
        from bga.ingest.loader import load_run_context

        run = _slept_run(tmp_path, "awake", 0)
        context = load_run_context(str(run / "run-context.json"))
        assert context.suspension is None
        assert context.incomplete_reason is None

    def test_analyze_banners_it_and_names_the_fix(self, tmp_path):
        rendered = _bga(["analyze", str(_slept_run(tmp_path, "slept", 2700.0))]).stdout
        assert "spans a suspend" in rendered
        assert "45 minutes" in rendered, "the reader is told how much time was lost"
        assert "--inhibit" in rendered, (
            "the sentence must name the fix - the reader has a capture they "
            "cannot use and the next question is what to do differently")
        assert "DID NOT FINISH" in rendered

    def test_compare_refuses_the_verdict(self, tmp_path):
        payload = json.loads(_bga([
            "compare", str(_slept_run(tmp_path, "a", 0)),
            str(_slept_run(tmp_path, "b", 2700.0)), "--format", "json",
        ]).stdout)
        assert payload["verdict"].startswith("not comparable")
        assert "spans a suspend" in payload["verdict"]

    def test_it_is_not_called_a_failure(self, tmp_path):
        """Nothing failed and nobody interrupted it. Saying either sends
        the reader hunting for a compile error that does not exist."""
        rendered = _bga(["analyze", str(_slept_run(tmp_path, "slept", 600.0))]).stdout
        # The prose a reader sees, not the raw violation dump below it -
        # that dict legitimately carries `interrupted: False`, and
        # asserting over it would be asserting about a debug rendering.
        prose = rendered.split("Violations", 1)[0]
        assert "ended in FAILURE" not in prose
        assert "THIS BUILD FAILED" not in prose
        assert "interrupted" not in prose.lower()

    def test_the_gate_fails_closed(self, tmp_path):
        result = _bga(["compare", str(_slept_run(tmp_path, "a", 0)),
                       str(_slept_run(tmp_path, "b", 2700.0)),
                       "--fail-on-regression"])
        assert result.returncode == 6, result.stderr


class TestDoctorSuggestsIt:
    def test_it_speaks_only_where_a_sleep_policy_is_detectable(self, monkeypatch):
        from tools import bga_doctor

        monkeypatch.setattr(bga_doctor.shutil, "which", lambda _name: None)
        assert bga_doctor.check_sleep_policy() is None, (
            "a machine with no systemctl has no sleep policy to warn about")

    def test_it_warns_rather_than_fails(self):
        from tools import bga_doctor

        found = bga_doctor.check_sleep_policy()
        if found is not None:   # this container has systemd
            assert found["status"] in ("ok", "warn")
            if found["status"] == "warn":
                assert "--inhibit" in found["remedy"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
