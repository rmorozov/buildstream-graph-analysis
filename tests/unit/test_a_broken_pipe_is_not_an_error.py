"""A reader that stops reading is not a bga failure.

UX-575: `bga analyze RUN --format json | head -2` - the pipe
`docs/guides/cli.md` documents - printed a `BrokenPipeError` traceback
and exited 2. Two shapes, and a handler needs both: the write that
raises inside the process, and the short output that raises nothing
until the interpreter flushes at exit, which is past every `except` in
the process and costs exit 120.

The subprocess env drops `PYTHONUNBUFFERED`, which this container sets:
with it, stdout is unbuffered, every write syscalls at the call site,
and the second shape cannot happen at all. A guard that inherited it
would be measuring an interpreter no user runs.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
RUN = REPO / "tests" / "fixtures" / "macro_micro" / "run"

# Every command whose `--schema` prints a JSON document (UX-190).
EMITTERS = ["analyze", "compare", "blast", "correlate", "whatif"]


def _buffered_env() -> dict:
    env = dict(os.environ)
    env.pop("PYTHONUNBUFFERED", None)
    env["PYTHONPATH"] = str(REPO)
    return env


def _pipe_then_stop(argv: list[str], read_lines: int) -> tuple[int, str, list[str]]:
    """Run `bga <argv>` and close stdout after `read_lines` lines - `head`.

    `read_lines=0` closes before the child has written anything, which is
    the only shape a *small* output can break on: four of the five
    schemas below fit the kernel's 64K pipe buffer whole, so a reader
    that takes three lines first and then leaves never breaks the pipe
    at all, and the case passes whatever the handler does. Measured:
    analyze 115783 bytes, correlate 26768, compare 17435, blast 4519,
    whatif 3375.
    """
    proc = subprocess.Popen(
        [sys.executable, "-m", "bga.cli", *argv],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=REPO, env=_buffered_env(),
    )
    lines = [proc.stdout.readline() for _ in range(read_lines)]
    proc.stdout.close()
    stderr = proc.stderr.read()
    proc.stderr.close()
    return proc.wait(timeout=120), stderr, lines


@pytest.mark.parametrize("command", EMITTERS)
def test_a_schema_whose_reader_left_exits_zero(command):
    code, stderr, _ = _pipe_then_stop([command, "--schema"], read_lines=0)

    assert "Traceback" not in stderr, stderr
    assert "BrokenPipeError" not in stderr, stderr
    assert "Exception ignored" not in stderr, stderr
    assert code == 0, f"{command} --schema into a closed pipe exited {code}: {stderr}"


def test_the_documented_analyze_pipe_prints_its_two_lines_and_exits_zero():
    code, stderr, lines = _pipe_then_stop(
        ["analyze", str(RUN), "--format", "json"], read_lines=2,
    )

    assert lines[0].strip() == "{"
    assert '"schema"' in lines[1]
    assert "Traceback" not in stderr, stderr
    assert "BrokenPipeError" not in stderr, stderr
    assert code == 0, stderr


def test_a_short_output_flushed_at_exit_does_not_reach_a_closed_pipe():
    """The second shape: nothing is written while `main` is on the stack.

    `--version` is bytes, not kilobytes, so it sits in the buffer; the
    reader is gone before the process writes at all. Without the flush
    inside the handler's `try`, the interpreter does it after `main`
    returned - "Exception ignored" on stderr, exit 120.
    """
    proc = subprocess.Popen(
        [sys.executable, "-m", "bga.cli", "--version"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=REPO, env=_buffered_env(),
    )
    proc.stdout.close()
    stderr = proc.stderr.read()
    proc.stderr.close()
    code = proc.wait(timeout=120)

    assert "Exception ignored" not in stderr, stderr
    assert "BrokenPipeError" not in stderr, stderr
    assert code == 0, f"exited {code}: {stderr}"


def test_stderr_is_untouched_when_the_pipe_breaks():
    """The contract's other half: exit 0 *silently*."""
    _, stderr, _ = _pipe_then_stop(["analyze", "--schema"], read_lines=0)

    assert stderr == "", stderr
