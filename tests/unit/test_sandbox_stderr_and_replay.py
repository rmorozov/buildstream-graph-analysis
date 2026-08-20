"""UX-148: a failed sandbox should leave its argv and its stderr behind.

`UX-146`'s record proves the rewrite happened, and then the shim *becomes*
the real bwrap - so whatever that process printed on failure belongs to
`buildbox-run`, which on at least one real stack reports only a return
code. A user with the diagnostics file still could not answer "so what
did bwrap object to?", and nothing let anyone re-run the sandbox to find
out.
"""
import json
import os
import subprocess
import sys

from tools.bst_native_build_tracer import (
    format_sandbox_stderr, missing_bind_paths, read_invocations,
    replay_sandbox, sandbox_stderr_path,
)
from tools.native_trace.bwrap_shim import exit_like, run_teed, stderr_record_path


def _script(tmp_path, name, body):
    path = tmp_path / name
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(0o755)
    return str(path)


class TestTheTeeKeepsUx140sContract:
    """The reason this is `--diagnose`-only. UX-140 established that the
    shim *becoming* the real bwrap is what makes signals, exit status and
    process identity reach buildbox-run unchanged."""

    def test_stderr_reaches_both_the_file_and_the_caller(self, tmp_path, capfd):
        fake = _script(tmp_path, "bwrap", "echo 'bwrap: objection' >&2\nexit 1\n")
        sink = str(tmp_path / "out.stderr")

        status = run_teed(fake, [fake], sink)

        assert exit_like(status) == 1
        assert "bwrap: objection" in open(sink).read()
        # a tee, not a redirect: hiding it would suppress the very message
        # the user is chasing
        assert "bwrap: objection" in capfd.readouterr().err

    def test_a_signalled_sandbox_still_reaches_bst_as_signalled(self, tmp_path):
        """The UX-140 subprocess check, through the forked path. Measured
        in a child, because the re-raise kills whoever does it."""
        fake = _script(tmp_path, "bwrap", "kill -SEGV $$\n")
        sink = str(tmp_path / "out.stderr")
        program = (
            "import sys;"
            f"sys.path.insert(0, {os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))!r});"
            "from tools.native_trace.bwrap_shim import run_teed, exit_like;"
            f"sys.exit(exit_like(run_teed({fake!r}, [{fake!r}], {sink!r})))"
        )
        result = subprocess.run([sys.executable, "-c", program])
        assert result.returncode == -11, (
            "a signal-killed sandbox must reach bst as WIFSIGNALED, not as an "
            "ordinary exit code - that is UX-140's contract")

    def test_an_ordinary_exit_code_passes_through(self, tmp_path):
        fake = _script(tmp_path, "bwrap", "exit 42\n")
        assert exit_like(run_teed(fake, [fake], str(tmp_path / "e"))) == 42

    def test_a_missing_binary_reports_rather_than_tracebacks(self, tmp_path):
        sink = str(tmp_path / "e")
        status = run_teed(str(tmp_path / "gone"), ["gone"], sink)
        assert exit_like(status) == 127
        assert "could not exec" in open(sink).read()

    def test_the_stderr_directory_sits_beside_the_record(self, tmp_path):
        diagnostics = str(tmp_path / "d.jsonl")
        path = stderr_record_path(diagnostics, 4242)
        assert path == str(tmp_path / "d.jsonl.stderr" / "4242.stderr")
        assert os.path.isdir(os.path.dirname(path))


class TestTheSummaryQuotesWhatTheSandboxSaid:
    def _capture(self, tmp_path, rows):
        diagnostics = tmp_path / "d.jsonl"
        stderr_dir = tmp_path / "d.jsonl.stderr"
        stderr_dir.mkdir()
        with open(diagnostics, "w") as handle:
            handle.write(json.dumps({"record": "fingerprint"}) + "\n")
            for pid, element, text in rows:
                handle.write(json.dumps({
                    "pid": pid, "element": element, "exec_argv": ["/bin/true"],
                    "stderr_path": f"/gone/{pid}.stderr"}) + "\n")
                (stderr_dir / f"{pid}.stderr").write_text(text)
        return str(diagnostics)

    def test_it_quotes_the_failing_sandbox(self, tmp_path):
        path = self._capture(tmp_path, [(1, "a.bst", ""), (2, "b.bst", "bwrap: nope\n")])
        text = format_sandbox_stderr(path)
        assert "b.bst" in text and "bwrap: nope" in text

    def test_the_last_speaking_sandbox_is_the_one_that_died(self, tmp_path):
        """The build stops at its first failing element, so the sandbox that
        spoke last is the sandbox that died."""
        path = self._capture(tmp_path, [(1, "a.bst", "early noise\n"),
                                        (2, "b.bst", "the real failure\n")])
        assert "the real failure" in format_sandbox_stderr(path)

    def test_it_points_at_the_replay_command_with_the_right_index(self, tmp_path):
        path = self._capture(tmp_path, [(1, "a.bst", ""), (2, "b.bst", "x\n")])
        assert "replay-sandbox" in format_sandbox_stderr(path)
        assert "-n 2" in format_sandbox_stderr(path)

    def test_a_silent_capture_says_nothing(self, tmp_path):
        path = self._capture(tmp_path, [(1, "a.bst", ""), (2, "b.bst", "")])
        assert format_sandbox_stderr(path) is None

    def test_a_long_tail_is_elided_with_a_pointer_to_the_file(self, tmp_path):
        path = self._capture(tmp_path, [(1, "a.bst", "\n".join(f"line {i}" for i in range(60)))])
        text = format_sandbox_stderr(path, tail_lines=5)
        assert "earlier line(s)" in text
        assert "line 59" in text and "line 10" not in text

    def test_the_live_path_wins_over_the_recorded_one(self, tmp_path):
        """The recorded path points into the capture's scratch, which
        UX-155 deletes - so a summary that trusted it found nothing. The
        files are copied out beside the record; the live location is
        derived, and the recorded path is only a fallback."""
        path = self._capture(tmp_path, [(7, "a.bst", "kept\n")])
        row = read_invocations(path)[0]
        assert row["stderr_path"].startswith("/gone/")
        assert sandbox_stderr_path(path, row).endswith("d.jsonl.stderr/7.stderr")


class TestReplaySandbox:
    def _record(self, tmp_path, argv, element="e.bst"):
        path = tmp_path / "d.jsonl"
        with open(path, "w") as handle:
            handle.write(json.dumps({"record": "fingerprint"}) + "\n")
            handle.write(json.dumps({
                "pid": 5, "element": element, "exec_argv": argv}) + "\n")
        return str(path)

    def test_it_runs_the_recorded_argv(self, tmp_path, capfd):
        marker = tmp_path / "ran"
        fake = _script(tmp_path, "bwrap", f"touch {marker}\n")
        assert replay_sandbox(self._record(tmp_path, [fake])) == 0
        assert marker.exists()

    def test_dry_run_prints_without_running(self, tmp_path, capfd):
        marker = tmp_path / "ran"
        fake = _script(tmp_path, "bwrap", f"touch {marker}\n")
        assert replay_sandbox(self._record(tmp_path, [fake]), dry_run=True) == 0
        assert not marker.exists()
        assert fake in capfd.readouterr().out

    def test_it_refuses_politely_when_a_bind_is_gone(self, tmp_path, capfd):
        """Sandbox roots are ephemeral, so a partially expired recording is
        the common case - and a confusing error here would recreate the
        problem this fixes."""
        record = self._record(
            tmp_path, ["/bin/true", "--bind", "/gone/staging/xyz", "/x"])
        assert replay_sandbox(record) == 2
        err = capfd.readouterr().err
        assert "/gone/staging/xyz" in err
        assert "no longer exist" in err

    def test_it_names_every_missing_bind_flag_form(self):
        argv = ["/bin/true", "--ro-bind", "/gone/a", "/x",
                "--dev-bind", "/gone/b", "/y", "--bind", "/tmp", "/z"]
        assert missing_bind_paths(argv) == ["/gone/a", "/gone/b"]

    def test_a_relative_or_special_bind_is_not_mistaken_for_a_path(self):
        assert missing_bind_paths(["/bin/true", "--bind", "relative", "/x"]) == []

    def test_listing_shows_which_invocations_spoke(self, tmp_path, capfd):
        path = tmp_path / "d.jsonl"
        stderr_dir = tmp_path / "d.jsonl.stderr"
        stderr_dir.mkdir()
        with open(path, "w") as handle:
            handle.write(json.dumps({"pid": 1, "element": "a.bst",
                                     "exec_argv": ["/bin/true"]}) + "\n")
            handle.write(json.dumps({"pid": 2, "element": "b.bst",
                                     "exec_argv": ["/bin/true"]}) + "\n")
        (stderr_dir / "2.stderr").write_text("said something\n")
        assert replay_sandbox(str(path), listing=True) == 0
        out = capfd.readouterr().out
        assert "a.bst" in out and "b.bst" in out
        assert "bytes of stderr" in out

    def test_an_out_of_range_index_says_the_range(self, tmp_path, capfd):
        record = self._record(tmp_path, ["/bin/true"])
        assert replay_sandbox(record, index=9) == 2
        assert "between 1 and 1" in capfd.readouterr().err

    def test_an_empty_record_explains_rather_than_crashing(self, tmp_path, capfd):
        empty = tmp_path / "d.jsonl"
        empty.write_text("")
        assert replay_sandbox(str(empty)) == 2
        assert "No invocations recorded" in capfd.readouterr().err


class TestTheDefaultPathStillExecs:
    def test_the_shim_only_tees_under_diagnose(self):
        """`--diagnose` is a one-session debugging mode, so the extra
        process is in scope there and only there. Everywhere else the pure
        exec is the contract."""
        import inspect
        from tools.native_trace import bwrap_shim
        source = inspect.getsource(bwrap_shim.main)
        tee_line = [ln for ln in source.splitlines() if "run_teed" in ln]
        assert tee_line, "the tee must be reachable"
        assert "if stderr_path:" in source
        assert "os.execv(real_bwrap, argv)" in source, "the default path still execs"
