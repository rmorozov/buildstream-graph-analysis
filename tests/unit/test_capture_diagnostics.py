"""UX-146: a capture that fails should say something about why.

Filed from a real report, not an audit: `bst build` succeeds,
`bga snapshot` fails with `buildbox-run failed with returncode 1`, and
turning off both optional mechanisms changes nothing. Three unrelated
causes produce that sentence - the `$PATH` shadow never reaching
`buildbox-run`, the argv rewrite mis-splitting, or the environment - and
from outside they are the same silence.

What these pin is the part that makes the record worth sending: that
zero invocations reads as its own finding rather than as an absence,
that both argvs are kept, and that `--no-inject` says plainly it
measured nothing.
"""
import json
import os

import pytest

from tools.bst_native_build_tracer import (
    format_capture_diagnostics, read_capture_diagnostics,
)
from tools.native_trace.bwrap_shim import record_diagnostics

# A real BuildStream-generated bwrap argv, trimmed to its shape.
REAL_ARGV = [
    "--unshare-pid", "--die-with-parent",
    "--bind", "/cas/staging/tmp", "/",
    "--unshare-net", "--unshare-uts", "--hostname", "buildbox",
    "--dir", "/buildstream/my-project/core.bst",
    "--chdir", "/buildstream/my-project/core.bst",
    "sh", "-c", "-e", "make -j4",
]


@pytest.fixture
def record_path(tmp_path):
    return str(tmp_path / "capture-diagnostics.jsonl")


class TestTheRecordHoldsBothArgvs:
    def test_what_came_in_and_what_goes_out_are_both_kept(self, record_path):
        """One of them alone answers nothing: the rewrite is the suspect,
        so the comparison is the evidence."""
        exec_argv = ["/usr/bin/bwrap", *REAL_ARGV[:-4], "--bind", "/t", "/t",
                     "sh", "-c", "-e", "make -j4"]

        assert record_diagnostics(record_path, REAL_ARGV, exec_argv,
                                  "/usr/bin/bwrap", "core.bst", None, True)

        [entry] = read_capture_diagnostics(record_path)
        assert entry["received_argv"] == REAL_ARGV
        assert entry["exec_argv"] == exec_argv
        assert entry["element"] == "core.bst"
        assert entry["injected"] is True

    def test_the_split_point_is_recorded_because_it_is_the_fragile_part(
            self, record_path):
        """`split_bwrap_args`' arity table was validated against
        bubblewrap 0.9.0. A newer flag it does not know is assumed to
        take no arguments, which mis-splits silently."""
        record_diagnostics(record_path, REAL_ARGV, [], "/usr/bin/bwrap",
                           "core.bst", None, True)

        [entry] = read_capture_diagnostics(record_path)
        assert entry["command"] == ["sh", "-c", "-e", "make -j4"]
        assert entry["option_count"] == len(REAL_ARGV) - 4

    def test_one_line_per_invocation(self, record_path):
        for _ in range(3):
            record_diagnostics(record_path, REAL_ARGV, [], "/usr/bin/bwrap",
                               "core.bst", None, True)

        assert len(read_capture_diagnostics(record_path)) == 3

    def test_it_never_raises_on_an_unwritable_path(self, tmp_path):
        """A diagnostic that can fail a real build is worse than no
        diagnostic - the same rule `record_argv` follows."""
        assert record_diagnostics(str(tmp_path / "nope" / "x.jsonl"),
                                  REAL_ARGV, [], "/usr/bin/bwrap",
                                  None, None, True) is False

    def test_no_path_records_nothing(self):
        assert record_diagnostics(None, REAL_ARGV, [], "/b", None, None, True) is False

    def test_a_corrupt_line_does_not_lose_the_rest(self, record_path):
        record_diagnostics(record_path, REAL_ARGV, [], "/usr/bin/bwrap",
                           "a.bst", None, True)
        with open(record_path, "a") as handle:
            handle.write("{not json\n")
        record_diagnostics(record_path, REAL_ARGV, [], "/usr/bin/bwrap",
                           "b.bst", None, True)

        assert [e["element"] for e in read_capture_diagnostics(record_path)] == [
            "a.bst", "b.bst"]


class TestZeroIsTheAnswerThatMatters:
    """The whole reason the count leads. A capture that produced nothing
    has two causes that look identical from outside, and only one of them
    is about the sandbox at all."""

    def test_it_says_the_shim_never_ran_rather_than_going_quiet(self, record_path):
        open(record_path, "w").close()

        rendered = format_capture_diagnostics(record_path)

        assert "ran 0 times" in rendered
        assert "$PATH" in rendered

    def test_it_names_the_innocent_explanation_too(self, record_path):
        """A fully cached build launches no sandbox at all, so zero is
        not always a fault - observed live on the second snapshot of an
        unchanged project."""
        open(record_path, "w").close()

        assert "cached build launches none" in format_capture_diagnostics(record_path)

    def test_a_missing_file_reads_the_same_as_an_empty_one(self, tmp_path):
        assert "ran 0 times" in format_capture_diagnostics(
            str(tmp_path / "never-written.jsonl"))


class TestTheSummaryLeadsWithWhatWasAsked:
    def _write(self, path, count=2, **overrides):
        for index in range(count):
            entry = {
                "pid": 100 + index, "ppid": 1, "at": 0.0,
                "real_bwrap": "/usr/bin/bwrap", "real_bwrap_executable": True,
                "element": f"e{index}.bst", "spine": None, "injected": True,
                "received_argv": REAL_ARGV, "exec_argv": REAL_ARGV,
                "option_count": 14, "command": ["sh", "-c", "-e", "make"],
            }
            entry.update(overrides)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry) + "\n")

    def test_the_count_and_the_split_between_modes(self, record_path):
        self._write(record_path, count=2)
        self._write(record_path, count=1, injected=False, element="e9.bst")

        rendered = format_capture_diagnostics(record_path)

        assert "ran 3 time(s); 2 rewritten, 1 passed through" in rendered

    def test_a_command_starting_with_an_option_is_called_out(self, record_path):
        """What a mis-split looks like: options leaking into the
        sandboxed command."""
        self._write(record_path, count=1, command=["--unknown-flag", "sh", "-c"])

        rendered = format_capture_diagnostics(record_path)

        assert "starts with an option" in rendered
        assert "bubblewrap 0.9.0" in rendered

    def test_a_normal_command_is_not_called_out(self, record_path):
        self._write(record_path, count=1)

        assert "starts with an option" not in format_capture_diagnostics(record_path)

    def test_an_unexecutable_bwrap_is_named_as_fatal(self, record_path):
        self._write(record_path, count=1, real_bwrap_executable=False)

        assert "found no executable bwrap" in format_capture_diagnostics(record_path)

    def test_elements_the_shim_could_not_name_are_said_so(self, record_path):
        """Under a build-root override that is every element (UX-56), and
        "no elements" must not read as "no sandboxes"."""
        self._write(record_path, count=2, element=None)

        assert "none recoverable" in format_capture_diagnostics(record_path)

    def test_no_inject_says_it_measured_nothing(self, record_path):
        self._write(record_path, count=2, injected=False)

        rendered = format_capture_diagnostics(record_path, no_inject=True)

        assert "nothing was captured" in rendered
        assert "argv rewrite is at fault" in rendered

    def test_without_no_inject_that_paragraph_is_absent(self, record_path):
        self._write(record_path, count=2)

        assert "nothing was captured" not in format_capture_diagnostics(record_path)


class TestTheShimActuallyWritesIt:
    """Found by falsification: deleting the shim's own call to
    `record_diagnostics` broke nothing, because every other test in this
    file calls the recorder directly. Testing a function is not testing
    that anything invokes it."""

    def _run_shim(self, tmp_path, extra_env=None):
        import subprocess
        import sys

        from tools.native_trace import bwrap_shim

        fake_bwrap = tmp_path / "fake-bwrap"
        fake_bwrap.write_text("#!/bin/sh\nexit 0\n")
        fake_bwrap.chmod(0o755)
        record = tmp_path / "diag.jsonl"
        env = dict(os.environ)
        env.update({
            "BST_TRACE_REAL_BWRAP": str(fake_bwrap),
            "BST_TRACE_BIND_SRC": str(tmp_path),
            "BST_TRACE_BIND_DST": "/tmp/.bst-native-trace",
            "BST_TRACE_PRELOAD_SO": "/tmp/.bst-native-trace/hook.so",
            "BST_TRACE_LOG_DST": "/tmp/.bst-native-trace/trace.log",
            "BST_TRACE_DIAGNOSTICS": str(record),
        })
        env.update(extra_env or {})
        result = subprocess.run(
            [sys.executable, bwrap_shim.__file__, *REAL_ARGV],
            capture_output=True, text=True, env=env, timeout=120)
        assert result.returncode == 0, result.stderr
        return read_capture_diagnostics(str(record))

    def test_a_real_shim_run_leaves_a_record(self, tmp_path):
        [entry] = self._run_shim(tmp_path)

        assert entry["received_argv"] == REAL_ARGV
        assert entry["element"] == "core.bst"
        assert entry["injected"] is True
        assert entry["exec_argv"] != REAL_ARGV, "the rewrite is not recorded"

    def test_no_inject_execs_buildstreams_argv_untouched(self, tmp_path):
        """The bisection only means anything if the passthrough really is
        one: same argv, plus the binary in front."""
        [entry] = self._run_shim(tmp_path, {"BST_TRACE_NO_INJECT": "1"})

        assert entry["injected"] is False
        assert entry["exec_argv"][1:] == REAL_ARGV
        assert not any("hook.so" in token for token in entry["exec_argv"])

    def test_without_the_variable_nothing_is_written(self, tmp_path):
        """Opt-in: the record costs a write per sandbox and is only ever
        wanted while debugging."""
        import subprocess
        import sys

        from tools.native_trace import bwrap_shim

        fake_bwrap = tmp_path / "fake-bwrap"
        fake_bwrap.write_text("#!/bin/sh\nexit 0\n")
        fake_bwrap.chmod(0o755)
        record = tmp_path / "diag.jsonl"
        env = dict(os.environ)
        env.update({
            "BST_TRACE_REAL_BWRAP": str(fake_bwrap),
            "BST_TRACE_BIND_SRC": str(tmp_path),
            "BST_TRACE_BIND_DST": "/tmp/.bst-native-trace",
            "BST_TRACE_PRELOAD_SO": "/tmp/.bst-native-trace/hook.so",
            "BST_TRACE_LOG_DST": "/tmp/.bst-native-trace/trace.log",
        })
        env.pop("BST_TRACE_DIAGNOSTICS", None)
        subprocess.run([sys.executable, bwrap_shim.__file__, *REAL_ARGV],
                       capture_output=True, text=True, env=env, timeout=120)

        assert not record.exists()


class TestAFailedExecReportsItself:
    """It used to be a Python traceback on `buildbox-run`'s stderr, which
    BuildStream summarises as `buildbox-run failed with returncode 1` and
    buries in an element log."""

    def _run_shim(self, tmp_path, real_bwrap):
        import subprocess
        import sys

        from tools.native_trace import bwrap_shim

        env = dict(os.environ)
        env.update({
            "BST_TRACE_REAL_BWRAP": real_bwrap,
            "BST_TRACE_BIND_SRC": str(tmp_path),
            "BST_TRACE_BIND_DST": "/tmp/.bst-native-trace",
            "BST_TRACE_PRELOAD_SO": "/tmp/.bst-native-trace/hook.so",
            "BST_TRACE_LOG_DST": "/tmp/.bst-native-trace/trace.log",
        })
        return subprocess.run(
            [sys.executable, bwrap_shim.__file__, *REAL_ARGV],
            capture_output=True, text=True, env=env, timeout=120)

    def test_a_missing_bwrap_is_one_sentence_naming_it(self, tmp_path):
        result = self._run_shim(tmp_path, str(tmp_path / "no-such-bwrap"))

        assert result.returncode == 127, result.stderr
        assert "could not exec the real bwrap" in result.stderr
        assert "no-such-bwrap" in result.stderr
        assert "Traceback" not in result.stderr

    def test_it_names_the_variable_that_would_fix_it(self, tmp_path):
        result = self._run_shim(tmp_path, str(tmp_path / "no-such-bwrap"))

        assert "BST_TRACE_REAL_BWRAP" in result.stderr
