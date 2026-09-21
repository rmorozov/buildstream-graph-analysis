"""UX-883: UX-878's compiler-safe scrub is silent - the operator only
learns an element was narrowed by hitting the ICE or reading round
docs. This guards `lto_preflight_warnings` directly (the four input
classes) and once through `run_traced_build` itself (Popen faked, the
shim's own artifacts written the way a real sandbox would), so the
warning is proven on the actual emit path, not a re-derivation of it.
"""
import json
import os

from tools import bst_native_build_tracer as tracer
from tools.native_trace.bwrap_shim import _make_probe_cache_path


def _decision(element, policy, kind="cmake"):
    return {"element": element, "max_jobs": 4, "decision": "joined",
            "kind": kind, "policy": policy}


def _write_probe(jobserver_fifo, element, version, available=True):
    cache_path = _make_probe_cache_path(jobserver_fifo, element)
    with open(cache_path, "w", encoding="utf-8") as handle:
        json.dump({"available": available, "version": version}, handle)


class TestLtoPreflightWarnings:
    def test_a_scrubbed_policy_on_make_4_3_warns(self, tmp_path):
        """`cargo` rather than `cmake_meson`: UX-913 left the scrub in
        place only for the policies with no shim between an unwrapped
        client and MAKEFLAGS, and this is the line that names it."""
        fifo = str(tmp_path / "jobserver")
        _write_probe(fifo, "core.bst", "GNU Make 4.3")

        lines = tracer.lto_preflight_warnings(
            [_decision("core.bst", "cargo")], fifo)

        assert len(lines) == 1
        assert "core.bst" in lines[0]
        assert "make >=4.4" in lines[0]

    def test_a_shim_defused_policy_on_make_4_3_says_the_auth_was_kept(
            self, tmp_path):
        """UX-913's other side. Silence here would be the defect this row
        was filed for: a reader could not tell an engaged mode from a
        warning that stopped firing, which is how eight CI pairs carried
        `peak 2` with nobody reading them."""
        fifo = str(tmp_path / "jobserver")
        _write_probe(fifo, "core.bst", "GNU Make 4.3")

        lines = tracer.lto_preflight_warnings(
            [_decision("core.bst", "cmake_meson")], fifo)

        assert len(lines) == 1
        assert "core.bst" in lines[0]
        assert "keeps its jobserver auth" in lines[0]
        assert "scrubbed" not in lines[0]

    def test_make_4_4_gets_no_warning(self, tmp_path):
        fifo = str(tmp_path / "jobserver")
        _write_probe(fifo, "core.bst", "GNU Make 4.4")

        lines = tracer.lto_preflight_warnings(
            [_decision("core.bst", "cmake_meson")], fifo)

        assert lines == []

    def test_a_non_compiler_kind_on_make_4_3_gets_no_warning(self, tmp_path):
        fifo = str(tmp_path / "jobserver")
        _write_probe(fifo, "core.bst", "GNU Make 4.3")

        lines = tracer.lto_preflight_warnings(
            [_decision("core.bst", "make", kind="make")], fifo)

        assert lines == []

    def test_boundary_exactly_4_4_is_no_warning(self, tmp_path):
        """The cutoff `style_for_make_version` shares with UX-874/878:
        4.4 parses `fifo:` fine, so there is nothing to scrub."""
        fifo = str(tmp_path / "jobserver")
        _write_probe(fifo, "core.bst", "GNU Make 4.4.0")

        lines = tracer.lto_preflight_warnings(
            [_decision("core.bst", "jobs_env")], fifo)

        assert lines == []

    def test_two_elements_same_kind_and_version_each_get_one_line(self, tmp_path):
        fifo = str(tmp_path / "jobserver")
        _write_probe(fifo, "a.bst", "GNU Make 4.3")
        _write_probe(fifo, "b.bst", "GNU Make 4.3")

        lines = tracer.lto_preflight_warnings(
            [_decision("a.bst", "cargo"), _decision("b.bst", "cargo")], fifo)

        assert len(lines) == 2
        assert any("a.bst" in line for line in lines)
        assert any("b.bst" in line for line in lines)

    def test_a_repeated_decision_row_for_one_element_dedupes(self, tmp_path):
        fifo = str(tmp_path / "jobserver")
        _write_probe(fifo, "core.bst", "GNU Make 4.3")

        lines = tracer.lto_preflight_warnings(
            [_decision("core.bst", "cmake_meson"),
             _decision("core.bst", "cmake_meson")], fifo)

        assert len(lines) == 1

    def test_no_jobserver_fifo_means_nothing_was_probed(self, tmp_path):
        lines = tracer.lto_preflight_warnings(
            [_decision("core.bst", "cmake_meson")], None)

        assert lines == []

    def test_no_probe_cached_yet_is_silent_not_a_re_probe(self, tmp_path):
        """No cache file exists (the element's sandbox never ran through
        `_compiler_safe_makeflags`) - this reads, it never shells out."""
        fifo = str(tmp_path / "jobserver")

        lines = tracer.lto_preflight_warnings(
            [_decision("core.bst", "cmake_meson")], fifo)

        assert lines == []


class TestLtoPreflightThroughRunTracedBuild:
    """The emit path itself: `Popen` faked to stand in for the real
    sandbox build, but writing the same `jobserver_decisions.jsonl` and
    `make_probe-*.json` artifacts a real one leaves in `bind_dir` -
    `run_traced_build` reads them exactly the way a real capture would."""

    def _run(self, tmp_path, monkeypatch, decisions):
        project = tmp_path / "proj"
        project.mkdir()
        raw_log = tmp_path / "trace.log"
        monkeypatch.setattr(tracer, "compile_hook", lambda d: None)
        monkeypatch.setattr(tracer, "install_bwrap_shim", lambda d: "/usr/bin/bwrap")
        monkeypatch.setattr(tracer, "write_bwrap_shim", lambda d: os.path.join(d, "bwrap"))
        monkeypatch.setattr(tracer, "probe_bwrap_shim", lambda p: None)

        def fake_popen(cmd, cwd=None, env=None, **kwargs):
            jobserver_fifo = env["BST_TRACE_JOBSERVER"]
            bind_dir = os.path.dirname(jobserver_fifo)
            with open(os.path.join(bind_dir, "jobserver_decisions.jsonl"),
                      "w", encoding="utf-8") as handle:
                for row in decisions:
                    probe = row.pop("_probe", None)
                    handle.write(json.dumps(row) + "\n")
                    if probe is not None:
                        _write_probe(jobserver_fifo, row["element"], probe)

            class _Proc:
                def wait(self):
                    return 0
            return _Proc()

        monkeypatch.setattr(tracer.subprocess, "Popen", fake_popen)
        tracer.run_traced_build(str(project), ["bst", "build", "x.bst"],
                                str(raw_log), jobserver=4)

    def test_stderr_names_the_element_and_the_remedy(self, tmp_path, monkeypatch, capsys):
        self._run(tmp_path, monkeypatch, [
            {**_decision("core.bst", "cargo"), "_probe": "GNU Make 4.3"},
        ])

        err = capsys.readouterr().err
        assert "core.bst" in err
        assert "make >=4.4" in err

    def test_stderr_carries_the_kept_auth_line_too(self, tmp_path, monkeypatch, capsys):
        """The capture's own warnings are the only place a reader sees
        this decision (UX-913), so the shim route has to reach stderr by
        the same path the scrub line does."""
        self._run(tmp_path, monkeypatch, [
            {**_decision("core.bst", "cmake_meson"), "_probe": "GNU Make 4.3"},
        ])

        err = capsys.readouterr().err
        assert "keeps its jobserver auth" in err

    def test_make_4_4_prints_nothing(self, tmp_path, monkeypatch, capsys):
        self._run(tmp_path, monkeypatch, [
            {**_decision("core.bst", "cmake_meson"), "_probe": "GNU Make 4.4"},
        ])

        err = capsys.readouterr().err
        assert "core.bst" not in err

    def test_a_non_compiler_kind_prints_nothing(self, tmp_path, monkeypatch, capsys):
        self._run(tmp_path, monkeypatch, [
            {**_decision("core.bst", "make", kind="make"), "_probe": "GNU Make 4.3"},
        ])

        err = capsys.readouterr().err
        assert "core.bst" not in err
