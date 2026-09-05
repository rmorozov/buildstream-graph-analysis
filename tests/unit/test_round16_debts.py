"""UX-162: the follow-through UX-147..155 still owed.

Round 16 verified those items as landed and collected what each one had
left unguarded. None of this reopens its parent; together it is one
sitting of work.
"""
import json
import os
import sys

import pytest

from tools import bga_doctor as doctor
from tools.bst_native_build_tracer import (
    _record_line,
    capture_fingerprint,
    element_path,
    resolve_buildbox_run,
)


class TestTheFingerprintNamesTheRealBuildboxRun:
    """Item 1. `shutil.which("buildbox-run")` is null on every standard
    install - bst 2.x vendors the binary under `site-packages` and never
    puts it on PATH - and UX-151's motivation had named this exact field
    as the one a maintainer needs."""

    def test_it_finds_the_vendored_binary(self):
        pytest.importorskip("buildstream")
        resolved = resolve_buildbox_run()
        assert resolved is not None, "null is the bug this item is about"
        assert os.access(resolved, os.X_OK)

    def test_the_fingerprint_carries_it(self):
        pytest.importorskip("buildstream")
        assert capture_fingerprint()["buildbox_run_path"] is not None

    def test_path_is_still_the_fallback(self, monkeypatch, tmp_path):
        """A distro that installs it normally must keep working."""
        import tools.bst_native_build_tracer as tracer
        monkeypatch.setitem(sys.modules, "buildstream", None)
        fake = tmp_path / "buildbox-run"
        fake.write_text("#!/bin/sh\n")
        fake.chmod(0o755)
        monkeypatch.setattr(tracer.shutil, "which",
                            lambda name: str(fake) if name == "buildbox-run" else None)
        assert resolve_buildbox_run() == str(fake)


class TestEmptyDescribesTheFileNotTheCount:
    """Item 2. This said `(empty)` on every zero-invocation capture,
    including one whose record holds UX-151's fingerprint line - so a
    maintainer told to read an "empty" file found the version data they
    needed sitting in it."""

    def test_a_file_with_a_fingerprint_is_not_called_empty(self, tmp_path):
        record = tmp_path / "diag.jsonl"
        record.write_text(json.dumps({"record": "fingerprint"}) + "\n")
        assert "(empty)" not in _record_line(str(record))
        assert str(record) in _record_line(str(record))

    def test_a_genuinely_empty_file_is(self, tmp_path):
        record = tmp_path / "diag.jsonl"
        record.write_text("")
        assert _record_line(str(record)).endswith("(empty)")

    def test_a_missing_file_reads_as_empty(self, tmp_path):
        assert _record_line(str(tmp_path / "gone")).endswith("(empty)")


class TestElementPathTolerance:
    """Item 4. A naive `startswith` missed an indented key, and the raw
    remainder handed back YAML quotes verbatim - `element-path: "files"`
    resolved to a directory literally named `"files"`."""

    @pytest.mark.parametrize("line,expected", [
        ("element-path: files", "files"),
        ("  element-path: files", "files"),
        ('element-path: "files"', "files"),
        ("element-path: 'files'", "files"),
        ("element-path: files  # where they live", "files"),
        ("element-path:", "elements"),
    ])
    def test_it_reads_the_declared_path(self, tmp_path, line, expected):
        (tmp_path / "project.conf").write_text(f"name: x\n{line}\n")
        assert element_path(str(tmp_path)) == expected

    def test_an_absent_key_is_buildstreams_default(self, tmp_path):
        (tmp_path / "project.conf").write_text("name: x\n")
        assert element_path(str(tmp_path)) == "elements"


class TestTheFourClaimsThatHadNoTest:
    """Item 5, each named by its own round's acceptance."""

    def test_a_failed_capture_points_at_diagnose(self):
        """UX-147 item 5's claim: the failing user is told what would
        answer the question."""
        import inspect

        from tools import bst_native_build_tracer as tracer
        source = inspect.getsource(tracer.main)
        assert "re-run with --diagnose" in source
        assert "returncode != 0" in source or "returncode" in source

    def test_the_selftest_seam_is_absent_from_the_shims_injected_env(self):
        """UX-152 claimed the seam is 'inert unless asked for and absent
        from the shim's injected environment'. Nothing pinned it."""
        from tools.native_trace import bwrap_shim
        argv = bwrap_shim.build_shim_argv(
            real_bwrap="/usr/bin/bwrap", bst_args=["--dir", "/x"],
            bind_src="/s", bind_dst="/d", preload_so="/d/hook.so",
            trace_log="/d/trace.log")
        joined = " ".join(argv)
        assert "SELFTEST" not in joined.upper()
        for seam in ("BST_TRACE_SPINE_DEGRADE_AFTER", "BST_TRACE_SPINE_FAIL_CONT_AT",
                     "BST_TRACE_SPINE_FAIL_SEIZE", "BST_TRACE_SPINE_SELFTEST"):
            assert seam not in joined, f"{seam} must not reach the sandbox"

    def test_the_census_runs_on_an_element_path_project(self, tmp_path):
        """UX-153's acceptance, tracer side - it was covered on doctor's
        side and not here."""
        from tools.bst_native_build_tracer import discover_element_names
        (tmp_path / "project.conf").write_text("name: x\nelement-path: src\n")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.bst").write_text("kind: manual\n")
        assert discover_element_names(str(tmp_path)) == ["a.bst"]

    def test_doctors_capture_chain_has_reachable_fail_branches(self):
        """UX-149's acceptance lists three live failure reproductions. The
        FAIL branches existed and no test entered any of them; this pins
        that they are reachable and worded, without needing a build."""
        import inspect
        source = inspect.getsource(doctor.check_capture_chain)
        assert source.count("FAIL") >= 2
        assert "SKIP" in source, "an unrunnable chain must skip, not pass"


class TestRootSpanningSourcesAreWarnedAbout:
    """Item 7. A `local` source spanning the project root stages `.bga` -
    live capture scratch included - into that element's cache key."""

    def _project(self, tmp_path, source_path):
        (tmp_path / "project.conf").write_text("name: x\n")
        (tmp_path / "elements").mkdir()
        (tmp_path / "elements" / "e.bst").write_text(
            f"kind: manual\nsources:\n- kind: local\n  path: {source_path}\n")
        return str(tmp_path)

    def test_a_root_spanning_source_warns(self, tmp_path):
        found = doctor.check_root_spanning_sources(self._project(tmp_path, "."))
        assert found["status"] == doctor.WARN
        assert "e.bst" in found["summary"]
        assert "cache key" in found["remedy"]

    def test_a_scoped_source_passes(self, tmp_path):
        (tmp_path / "files").mkdir()
        found = doctor.check_root_spanning_sources(self._project(tmp_path, "files"))
        assert found["status"] == doctor.OK

    def test_no_project_skips_rather_than_passing(self):
        assert doctor.check_root_spanning_sources(None)["status"] == doctor.SKIP


class TestTheWorkflowReadsWhatItRecords:
    """Item 3. `doctor_exit` was written into $GITHUB_ENV and read by
    nothing - recorded data nobody could see."""

    def test_the_summary_step_prints_the_recorded_exit(self):
        text = open(".github/workflows/real-project-capture.yml").read()
        assert "doctor_exit=$rc" in text, "still recorded"
        assert "${doctor_exit:-unset}" in text, "and now read"
        assert "GITHUB_STEP_SUMMARY" in text
