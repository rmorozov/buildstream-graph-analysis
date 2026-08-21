"""UX-188: one timeline, both planes, one command.

Field feedback: *"recheck that we can produce chrome:tracing compatible
output for plane2 capture — maybe we can make some kind of merge tool
that can merge timeline from plane 1 and plane 2."*

Round 20 found the merge already existed and worked. What did not exist
was any way for a user to reach it: snapshots did not retain the raw
Plane 2 log `combined` mode reads, feeding it the wrong file succeeded
silently, and composing the three commands took invented paths.

So these guards are mostly about the *route*, not the arithmetic - the
merge itself is `UX-24`'s and already tested.
"""
import gzip
import json
import os
import shutil
import subprocess
import sys

import pytest

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

# A minimal wrapped Plane 1 log and the raw Plane 2 lines that pair with
# it: two elements, one of which ran a process. Written by hand so the
# guards do not need a real `bst`.
_WRAPPED = """[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:work-a.bst] START Building
[wrapper][2026-08-21 12:00:03,100] INFO: [00:00:03][aaaaaaaa][   build:work-a.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:03,200] INFO: Return code: 0
"""

_RAW = """START pid=101 ppid=1 ts=1000.000000 element=work-a.bst cmd=cc -c main.c
END pid=101 ppid=1 ts=1002.500000 element=work-a.bst cmd=cc -c main.c
"""


def _bga(args, cwd=None):
    return subprocess.run(
        [sys.executable, "-c",
         "from bga.cli import main; raise SystemExit(main(%r))" % (args,)],
        capture_output=True, text=True, cwd=cwd or os.getcwd())


def _snapshot(tmp_path, with_raw=True, compressed=True):
    """A snapshot directory shaped like one `bga snapshot` writes."""
    snapshot = tmp_path / "20260821T120000Z"
    snapshot.mkdir()
    (snapshot / "build.log").write_text(_WRAPPED)
    shutil.copytree(GOLDEN, snapshot / "run")
    os.remove(snapshot / "run" / "expected_output.json")
    if with_raw:
        if compressed:
            with gzip.open(snapshot / "plane2.log.gz", "wt") as handle:
                handle.write(_RAW)
        else:
            (snapshot / "plane2.log").write_text(_RAW)
    return snapshot


class TestTheWrongFileIsRefused:
    def test_a_processed_report_is_not_a_raw_log(self, tmp_path):
        """The reproduction: `Wrote 0 trace events`, exit 0, from a
        `plane2.json` fed where a raw log belongs."""
        report = tmp_path / "plane2.json"
        report.write_text(json.dumps({"processes": [], "summary": {}}))
        out = tmp_path / "out.json"

        result = _bga(["native-to-chrome", "standalone", str(report), str(out)])
        assert result.returncode == 2, result.stdout
        assert "not empty" in result.stderr
        assert "plane2.json" in result.stderr, (
            "the message should name the mistake a user actually makes")

    def test_an_empty_file_still_passes(self, tmp_path):
        """A different claim: a capture that traced nothing really did
        produce no events, and refusing it would refuse a truth."""
        empty = tmp_path / "empty.log"
        empty.write_text("")
        result = _bga(["native-to-chrome", "standalone", str(empty),
                       str(tmp_path / "out.json")])
        assert result.returncode == 0, result.stderr

    def test_a_real_raw_log_passes(self, tmp_path):
        raw = tmp_path / "trace.log"
        raw.write_text(_RAW)
        out = tmp_path / "out.json"
        result = _bga(["native-to-chrome", "standalone", str(raw), str(out)])
        assert result.returncode == 0, result.stderr
        assert json.loads(out.read_text()), "no events written"


class TestTheConvertersLeaveStdoutAlone:
    """The payload is the file. A status line on stdout breaks
    `... /dev/stdout | jq`, and it is the one stderr-purity exception the
    tool had left."""

    def test_native_to_chrome(self, tmp_path):
        raw = tmp_path / "trace.log"
        raw.write_text(_RAW)
        result = _bga(["native-to-chrome", "standalone", str(raw),
                       str(tmp_path / "out.json")])
        assert result.stdout == "", result.stdout
        assert "Wrote" in result.stderr

    def test_log_to_chrome(self, tmp_path):
        log = tmp_path / "build.log"
        log.write_text(_WRAPPED)
        result = _bga(["log-to-chrome", str(log), str(tmp_path / "out.json")])
        assert result.stdout == "", result.stdout
        assert "Successfully generated" in result.stderr

    def test_chrome_to_trace(self, tmp_path):
        chrome = tmp_path / "chrome.json"
        chrome.write_text("[]")
        result = _bga(["chrome-to-trace", str(chrome), str(tmp_path / "trace.json")])
        assert result.stdout == "", result.stdout


class TestSnapshotsKeepTheRawLog:
    def test_the_name_and_the_compression_are_what_timeline_looks_for(self):
        from tools.bga_snapshot import RAW_LOG_NAME
        from tools.bga_timeline import RAW_LOG_NAME as EXPECTED

        assert RAW_LOG_NAME == EXPECTED == "plane2.log.gz", (
            "the writer and the reader must agree on the name, and nothing "
            "else in the codebase would notice if they stopped")

    def test_it_compresses_in_place(self, tmp_path):
        from tools.bga_snapshot import _compress_raw_log

        snapshot = tmp_path / "snap"
        snapshot.mkdir()
        (snapshot / "plane2.log").write_text(_RAW * 200)
        _compress_raw_log(str(snapshot))

        assert not (snapshot / "plane2.log").exists()
        with gzip.open(snapshot / "plane2.log.gz", "rt") as handle:
            assert handle.read() == _RAW * 200
        assert (snapshot / "plane2.log.gz").stat().st_size < len(_RAW * 200) / 2

    def test_a_capture_with_no_raw_log_is_not_an_error(self, tmp_path):
        """`--no-keep-raw`, and every snapshot taken before this."""
        from tools.bga_snapshot import _compress_raw_log

        snapshot = tmp_path / "snap"
        snapshot.mkdir()
        _compress_raw_log(str(snapshot))   # must not raise


class TestTheOneCommand:
    def test_it_renders_both_planes(self, tmp_path):
        from tools.bga_timeline import render

        snapshot = _snapshot(tmp_path)
        out = tmp_path / "timeline.json"
        result = render(str(snapshot), str(out))

        assert result["planes"] == ["1", "2"]
        assert result["anchor"] == "work-a.bst"
        events = json.loads(out.read_text())
        groups = {event["args"]["name"] for event in events
                  if event.get("name") == "process_name"}
        assert any(name.startswith("native:") for name in groups), (
            f"no Plane 2 lane group in {groups}")

    def test_it_reads_an_uncompressed_raw_log_too(self, tmp_path):
        """A capture whose compression failed keeps the plain file, and
        the timeline must still find it."""
        from tools.bga_timeline import render

        snapshot = _snapshot(tmp_path, compressed=False)
        result = render(str(snapshot), str(tmp_path / "t.json"))
        assert result["planes"] == ["1", "2"]

    def test_without_a_raw_log_it_renders_plane_1_and_says_what_is_missing(
            self, tmp_path):
        from tools.bga_timeline import describe, render

        snapshot = _snapshot(tmp_path, with_raw=False)
        out = tmp_path / "timeline.json"
        result = render(str(snapshot), str(out))

        assert result["planes"] == ["1"]
        assert json.loads(out.read_text()), "Plane 1 should still render"
        said = describe(result, str(out))
        assert "Plane 2 is not in it" in said
        assert "--no-keep-raw" in said, "the sentence should name the cause"

    def test_the_anchor_is_the_longest_traced_element(self, tmp_path):
        """A fixed alignment error is the smallest share of the longest
        span, and it is the element a reader is most likely opening the
        timeline to find."""
        from tools.bga_timeline import pick_anchor

        raw = tmp_path / "trace.log"
        raw.write_text(
            "START pid=1 ppid=0 ts=100.0 element=short.bst cmd=cc\n"
            "END pid=1 ppid=0 ts=100.5 element=short.bst cmd=cc\n"
            "START pid=2 ppid=0 ts=100.0 element=long.bst cmd=cc\n"
            "END pid=2 ppid=0 ts=180.0 element=long.bst cmd=cc\n")
        assert pick_anchor(str(raw)) == "long.bst"

    def test_an_explicit_anchor_wins(self, tmp_path):
        from tools.bga_timeline import render

        snapshot = _snapshot(tmp_path)
        result = render(str(snapshot), str(tmp_path / "t.json"),
                        anchor_element="work-a.bst")
        assert result["anchor"] == "work-a.bst"

    def test_a_run_directory_is_refused_with_the_fix(self, tmp_path):
        """The likeliest slip - `<snapshot>/run` instead of the snapshot -
        gets the sentence that names the difference, not a traceback."""
        from tools.bga_timeline import render

        snapshot = _snapshot(tmp_path)
        with pytest.raises(FileNotFoundError) as caught:
            render(str(snapshot / "run"), str(tmp_path / "t.json"))
        assert "try its parent" in str(caught.value)

    def test_stdout_carries_only_the_machine_summary(self, tmp_path):
        result = _bga(["timeline", str(_snapshot(tmp_path)),
                       "-o", str(tmp_path / "t.json")])
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["planes"] == ["1", "2"]
        assert "Perfetto" in result.stderr, "the human line goes to stderr"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
