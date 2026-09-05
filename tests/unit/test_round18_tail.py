"""UX-177: five corners round 18 verified its way into.

Each was demonstrated or traced by the review; none reopens its parent.
The first is the user-visible one - it breaks the paste-and-go property
UX-164 had just built.
"""
import os

import pytest

from bga import run_store
from tools import bst_native_build_tracer as tracer
from tools.bst_extract_run import _drop_size_memo

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _snapshot(project, name, with_run=True):
    path = project / ".bga" / "runs" / name
    (path / "run").mkdir(parents=True) if with_run else path.mkdir(parents=True)
    if with_run:
        (path / "run" / "trace.json").write_text("{}")
    return path


class TestAnExactStampWins:
    """UX-177 item 1, reproduced: the hint the tool printed, refused."""

    def _project(self, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        (project / "project.conf").write_text("name: p\nmin-version: 2.0\n")
        return project

    def test_a_full_stamp_that_is_a_prefix_of_its_sibling_resolves(self, tmp_path):
        project = self._project(tmp_path)
        _snapshot(project, "20260820T153932Z")
        _snapshot(project, "20260820T153932Z-01")
        resolved = run_store.resolve_snapshot("@20260820T153932Z", str(project))
        assert os.path.basename(resolved) == "20260820T153932Z"

    def test_the_sibling_still_resolves_by_its_own_full_name(self, tmp_path):
        project = self._project(tmp_path)
        _snapshot(project, "20260820T153932Z")
        _snapshot(project, "20260820T153932Z-01")
        resolved = run_store.resolve_snapshot("@20260820T153932Z-01", str(project))
        assert os.path.basename(resolved) == "20260820T153932Z-01"

    def test_a_genuinely_ambiguous_prefix_is_still_refused(self, tmp_path):
        """The exact-match win must not turn every prefix into a guess."""
        project = self._project(tmp_path)
        _snapshot(project, "20260820T153932Z")
        _snapshot(project, "20260820T153955Z")
        with pytest.raises(run_store.StoreError, match="matches 2 snapshots"):
            run_store.resolve_snapshot("@20260820T1539", str(project))

    def test_the_printed_hint_can_be_pasted(self, tmp_path):
        """End to end: the alias a walk-back would print, resolved."""
        project = self._project(tmp_path)
        newest = _snapshot(project, "20260820T153932Z")
        _snapshot(project, "20260820T153932Z-01")
        hint = f"@{os.path.basename(newest)}"
        assert run_store.resolve(hint, str(project)).startswith(str(newest))


class TestTheConfigFileIsSelectedByExistence:
    """UX-177 item 2: bst picks the *file*, then reads it - and stops."""

    def _config(self, tmp_path, monkeypatch, files):
        home = tmp_path / "config"
        home.mkdir()
        for name, text in files.items():
            (home / name).write_text(text)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(home))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
        return home

    def test_buildstream2_without_a_cachedir_does_not_fall_through(
            self, tmp_path, monkeypatch):
        """The corner: bst reads `buildstream2.conf` and takes its XDG
        default; falling through would answer with the other file's
        `cachedir`, a directory bst is not using."""
        self._config(tmp_path, monkeypatch, {
            "buildstream2.conf": "scheduler:\n  builders: 4\n",
            "buildstream.conf": "cachedir: /somewhere/else\n",
        })
        assert tracer.buildstream_cache_dir() == \
            str(tmp_path / "cache" / "buildstream")

    def test_buildstream2_with_a_cachedir_still_wins(self, tmp_path, monkeypatch):
        self._config(tmp_path, monkeypatch, {
            "buildstream2.conf": "cachedir: /two\n",
            "buildstream.conf": "cachedir: /one\n",
        })
        assert tracer.buildstream_cache_dir() == "/two"

    def test_only_the_older_file_is_read_when_it_is_the_only_one(
            self, tmp_path, monkeypatch):
        self._config(tmp_path, monkeypatch, {"buildstream.conf": "cachedir: /one\n"})
        assert tracer.buildstream_cache_dir() == "/one"


class TestOneNumberHasOneSource:
    def test_build_outcome_does_not_restate_the_queue_counts(self):
        """UX-177 item 3: the copy had no consumer, so it is gone.

        The `build_failed` violation derives these from `queue_summary`,
        which is the recorded source; a second spelling of the same
        number is how a drift finding starts.
        """
        source = open(
            os.path.join(REPO_ROOT, "tools", "bst_extract_run.py"),
            encoding="utf-8").read()
        assert '"built_count": counts["processed"]' not in source
        assert '"cached_count": counts["skipped"]' not in source


class TestTheSizeMemoDoesNotSurviveAReExtraction:
    def test_extracting_into_a_snapshot_drops_its_memo(self, tmp_path):
        """UX-177 item 4: an in-place overwrite moves no directory
        mtime, so UX-168's memo - keyed on exactly that - would survive
        a re-extraction that changed the snapshot's size."""
        snapshot = tmp_path / "20260820T120000Z"
        run = snapshot / "run"
        run.mkdir(parents=True)
        (run / "trace.json").write_text("x" * 100)
        first = run_store.snapshot_size_bytes(str(snapshot))
        assert (snapshot / run_store.SIZE_CACHE_NAME).exists()

        # Re-extraction: same file names, more content, same mtimes.
        _drop_size_memo(run)
        (run / "trace.json").write_text("x" * 5000)
        assert run_store.snapshot_size_bytes(str(snapshot)) > first

    def test_it_is_silent_for_a_run_directory_outside_a_store(self, tmp_path):
        run = tmp_path / "loose-run"
        run.mkdir()
        _drop_size_memo(run)  # must not raise


class TestTheStreamingReadersHandleCrlf:
    def test_a_crlf_trace_parses_the_same_as_an_lf_one(self):
        lines = [
            "START pid=2 ppid=1 ts=1.0 element=a.bst cmd=/usr/bin/cc",
            "END pid=2 ppid=1 ts=2.0 element=a.bst cmd=/usr/bin/cc",
        ]
        lf = tracer.parse_trace_lines(iter(line + "\n" for line in lines))
        crlf = tracer.parse_trace_lines(iter(line + "\r\n" for line in lines))
        assert lf == crlf
        assert crlf[0]["cmd"] == "/usr/bin/cc"

    def test_a_crlf_opens_block_parses_the_same(self):
        lines = [
            "OPENS pid=2 element=a.bst inv=none unique=1 dropped=0",
            "/usr/include/stdio.h",
        ]
        lf = tracer.parse_open_lines(iter(line + "\n" for line in lines))
        crlf = tracer.parse_open_lines(iter(line + "\r\n" for line in lines))
        assert lf == crlf
        assert crlf["a.bst"]["paths"] == {"/usr/include/stdio.h"}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
