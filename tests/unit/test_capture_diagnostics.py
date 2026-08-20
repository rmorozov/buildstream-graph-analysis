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
        unchanged project. UX-147 made the wording depend on whether any
        task actually ran; with no count it is still one of the three."""
        open(record_path, "w").close()

        assert "fully cached build" in format_capture_diagnostics(record_path)

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
        sandboxed command. UX-151 widened both the wording and the
        detector - a leading *operand* is the commoner shape."""
        self._write(record_path, count=1, command=["--unknown-flag", "sh", "-c"])

        rendered = format_capture_diagnostics(record_path)

        assert "does not look like one" in rendered
        assert "--unknown-flag" in rendered

    def test_a_command_starting_with_an_operand_is_called_out_too(self, record_path):
        self._write(record_path, count=1, command=["12", "--bind", "/x", "/"])

        assert "does not look like one" in format_capture_diagnostics(record_path)

    def test_a_normal_command_is_not_called_out(self, record_path):
        self._write(record_path, count=1)

        assert "does not look like one" not in format_capture_diagnostics(record_path)

    def test_unknown_flags_are_named_and_counted(self, record_path):
        """UX-151: the guess is arity 0 and there is no safer one, so the
        record names what was guessed about."""
        self._write(record_path, count=3, unknown_flags=["--brand-new"])

        rendered = format_capture_diagnostics(record_path)

        assert "not in the" in rendered and "arity table" in rendered
        assert "--brand-new (x3)" in rendered

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


class TestTheArityTableIsTheLikeliestFieldFailure:
    """UX-151: the table was validated on bubblewrap 0.9.0 and assumed
    any unknown `--flag` takes no arguments. A newer `buildbox-run`
    emitting one makes the split stop at that flag's *operand*, the
    rewritten argv is malformed, bwrap exits non-zero, and BuildStream
    reports `buildbox-run failed with returncode 1` — unchanged by
    turning either optional mechanism off, because the injection happens
    regardless. That is the reported field sentence, exactly."""

    def test_the_shape_that_produces_the_field_failure_now_splits(self):
        from tools.native_trace.bwrap_shim import split_bwrap_args

        argv = ["--json-status-fd", "12", "--bind", "/x", "/",
                "--unshare-pid", "sh", "-c", "make"]

        opts, command = split_bwrap_args(argv)

        assert command == ["sh", "-c", "make"], (
            "the fd operand was taken as the sandboxed command")
        assert "--json-status-fd" in opts and "12" in opts

    @pytest.mark.parametrize("flag,arity", [
        ("--seccomp", 1), ("--add-seccomp-fd", 1), ("--argv0", 1),
        ("--size", 1), ("--perms", 1), ("--remount-ro", 1), ("--mqueue", 1),
        ("--lock-file", 1), ("--userns", 1), ("--pidns", 1), ("--args", 1),
        ("--chmod", 2), ("--file", 2), ("--bind-data", 2),
        ("--bind-fd", 2), ("--ro-bind-fd", 2),
    ])
    def test_every_flag_the_finding_named_has_its_arity(self, flag, arity):
        from tools.native_trace.bwrap_shim import split_bwrap_args

        operands = [str(10 + i) for i in range(arity)]
        opts, command = split_bwrap_args([flag, *operands, "sh", "-c", "x"])

        assert command == ["sh", "-c", "x"], f"{flag} splits at its operand"
        assert opts == [flag, *operands]

    def test_the_three_argument_overlay_flag(self):
        """Post-0.9.0, and the only arity-3 option bwrap has."""
        from tools.native_trace.bwrap_shim import split_bwrap_args

        opts, command = split_bwrap_args(
            ["--overlay", "/rw", "/work", "/dest", "sh", "-c", "x"])

        assert command == ["sh", "-c", "x"]
        assert opts == ["--overlay", "/rw", "/work", "/dest"]

    def test_an_unknown_flag_is_reported_rather_than_guessed_silently(self):
        """The guess is still arity 0 - there is no safer one - but it is
        now a recorded condition naming the flag to add."""
        from tools.native_trace.bwrap_shim import unknown_flags

        assert unknown_flags(["--bind", "/a", "/b", "--brand-new", "sh"]) == [
            "--brand-new"]

    def test_a_known_argv_reports_no_unknowns(self):
        from tools.native_trace.bwrap_shim import unknown_flags

        assert unknown_flags(REAL_ARGV) == []


class TestTheMisSplitDetectorSeesTheShapesThatOccur:
    """UX-151: it checked `command[0].startswith("-")`, and the mis-splits
    a post-0.9.0 bwrap produces put the flag's operand first — a file
    descriptor, a size, an octal mode, all of which start with a digit.
    The one automated detector for the rewrite breaking missed the cases
    most likely to happen."""

    def _record(self, command):
        return {"command": command}

    def test_a_leading_flag(self):
        from tools.bst_native_build_tracer import _looks_mis_split

        assert _looks_mis_split(self._record(["--unknown", "sh", "-c"]))

    def test_a_leading_file_descriptor(self):
        from tools.bst_native_build_tracer import _looks_mis_split

        assert _looks_mis_split(self._record(["12", "--bind", "/x", "/"]))

    def test_a_separator_surviving_inside_the_command(self):
        from tools.bst_native_build_tracer import _looks_mis_split

        assert _looks_mis_split(self._record(["sh", "--", "-c", "make"]))

    def test_a_real_command_is_not_flagged(self):
        from tools.bst_native_build_tracer import _looks_mis_split

        assert not _looks_mis_split(self._record(["sh", "-c", "-e", "make -j4"]))

    def test_an_empty_command_is_not_flagged(self):
        """Absence is `--no-inject` or a parse that found nothing, both of
        which the summary reports by other means."""
        from tools.bst_native_build_tracer import _looks_mis_split

        assert not _looks_mis_split(self._record([]))


class TestTheRecordSaysWhatToParseAgainst:
    """UX-151: UX-146's motivation blames an arity table validated on one
    bubblewrap version, and then recorded no version of anything — so a
    maintainer reading a user's JSONL could not tell which table applied."""

    def test_the_fingerprint_names_the_versions_and_the_table(self):
        from tools.bst_native_build_tracer import capture_fingerprint

        fingerprint = capture_fingerprint()

        assert fingerprint["record"] == "fingerprint"
        assert fingerprint["arity_table_validated_against"] == "bubblewrap 0.9.0"
        assert "bwrap_path" in fingerprint and "bst_version" in fingerprint

    def test_it_is_not_counted_as_an_invocation(self, tmp_path):
        """"The shim ran 0 times" is the record's most important reading
        and a header line must not make it impossible to say."""
        from tools.bst_native_build_tracer import (
            capture_fingerprint, read_capture_diagnostics,
            read_capture_fingerprint,
        )

        path = tmp_path / "d.jsonl"
        path.write_text(json.dumps(capture_fingerprint()) + "\n")

        assert read_capture_diagnostics(str(path)) == []
        assert read_capture_fingerprint(str(path))["record"] == "fingerprint"
        assert "ran 0 times" in format_capture_diagnostics(str(path))


class TestZeroInvocationsHasThreeCausesNotOne:
    """UX-147: UX-146's summary asserted the benign one — *"this build
    ran unmodified"* — when in the reported field case it is the wrong
    one. The other two are the shim never being resolved (an absolute
    `bwrap` path, or a `buildbox-casd` started before the capture whose
    environment predates the shim directory) and the shim being resolved
    but failing to exec.

    The third is now excluded before the build runs, by the probe. What
    separates the other two is whether any sandbox was ever going to
    launch."""

    def test_no_tasks_is_the_cache_hit_reading_and_says_it_is_confirmed(
            self, record_path):
        open(record_path, "w").close()

        rendered = format_capture_diagnostics(record_path, sandbox_tasks=0)

        assert "no sandbox at all" in rendered
        assert "confirmed one" in rendered
        assert "never *resolved*" not in rendered

    def test_tasks_with_no_shim_lines_names_the_resolution_failure(
            self, record_path):
        open(record_path, "w").close()

        rendered = format_capture_diagnostics(record_path, sandbox_tasks=9)

        assert "9 element task(s)" in rendered
        assert "never *resolved*" in rendered
        assert "buildbox-casd" in rendered, "the ten-second fix is not named"
        assert "absolute path" in rendered

    def test_without_the_count_it_lists_all_three_rather_than_choosing(
            self, record_path):
        """"We could not tell" and "it was benign" are different claims."""
        open(record_path, "w").close()

        rendered = format_capture_diagnostics(record_path)

        assert "cannot tell them" in rendered

    def test_the_task_count_comes_from_the_plane_1_log(self, tmp_path):
        """`Running commands` is the phase that launches a sandbox -
        measured on examples/06 as 9 phases against 9 shim invocations.
        Staging and caching phases run inside BuildStream."""
        from tools.bst_native_build_tracer import count_build_tasks

        log = tmp_path / "build.log"
        log.write_text(
            "[--:--:--][][main:a.bst] START   Running commands\n"
            "[--:--:--][][main:a.bst] START   Staging sources\n"
            "[--:--:--][][main:b.bst] START   Running commands\n"
            "[--:--:--][][main:b.bst] START   Caching artifact\n")

        assert count_build_tasks(str(log)) == 2

    def test_a_missing_log_is_none_not_zero(self, tmp_path):
        """Zero means "nothing was going to launch a sandbox", which is a
        real finding. Absence must not be able to say it."""
        from tools.bst_native_build_tracer import count_build_tasks

        assert count_build_tasks(str(tmp_path / "nope.log")) is None
        assert count_build_tasks(None) is None


class TestTheShimIsProvedExecutableBeforeTheBuild:
    """UX-147 item 1: a noexec temp mount, an AppArmor rule on executing
    from `/tmp`, or an interpreter the sandbox layer cannot find all fail
    the shim's exec *inside* `buildbox-run` — which reports `returncode
    1` with stderr swallowed, an hour into a build, leaving an empty
    diagnostics record and a summary calling the build unmodified."""

    def test_a_freshly_installed_shim_answers_its_own_probe(self, tmp_path):
        from tools.bst_native_build_tracer import (
            probe_bwrap_shim, write_bwrap_shim,
        )

        write_bwrap_shim(str(tmp_path))
        probe_bwrap_shim(str(tmp_path / "bwrap"))   # raises on failure

    def test_the_shebang_is_an_absolute_interpreter(self, tmp_path):
        """`#!/usr/bin/env python3` makes the exec depend on the PATH of
        whatever process the sandbox layer hands it."""
        import sys

        from tools.bst_native_build_tracer import write_bwrap_shim

        write_bwrap_shim(str(tmp_path))

        assert (tmp_path / "bwrap").read_text().startswith(f"#!{sys.executable}\n")
        assert "/usr/bin/env" not in (tmp_path / "bwrap").read_text().split("\n")[0]

    def test_a_shim_that_cannot_be_executed_fails_with_the_reason(self, tmp_path):
        from tools.bst_native_build_tracer import (
            TraceError, probe_bwrap_shim, write_bwrap_shim,
        )

        write_bwrap_shim(str(tmp_path))
        os.chmod(tmp_path / "bwrap", 0o644)

        with pytest.raises(TraceError) as exc:
            probe_bwrap_shim(str(tmp_path / "bwrap"))

        assert "cannot be executed" in str(exc.value)
        assert "TMPDIR" in str(exc.value), "the remedy is not named"

    def test_the_shim_without_its_environment_falls_through_rather_than_raising(
            self, tmp_path):
        """UX-147 item 4: four bare `os.environ[...]` reads, four lines
        below the traceback UX-146 fixed. Anything else on the machine
        invoking `bwrap` while the shim directory is on PATH got a
        KeyError on buildbox-run's swallowed stderr."""
        import subprocess
        import sys

        from tools.bst_native_build_tracer import write_bwrap_shim

        write_bwrap_shim(str(tmp_path))
        real = tmp_path / "fake-bwrap"
        real.write_text("#!/bin/sh\nexit 42\n")
        real.chmod(0o755)
        env = {k: v for k, v in os.environ.items() if not k.startswith("BST_TRACE_")}
        env["BST_TRACE_REAL_BWRAP"] = str(real)

        result = subprocess.run([sys.executable, str(tmp_path / "bwrap"), "--version"],
                                capture_output=True, text=True, env=env, timeout=60)

        assert result.returncode == 42, result.stderr
        assert "Traceback" not in result.stderr
        assert "BST_TRACE_BIND_SRC" in result.stderr
