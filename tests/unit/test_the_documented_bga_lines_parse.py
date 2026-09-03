"""Every fenced `bga …` line is read by the parser that would run it.

UX-579: the older check (`test_docs_links_and_commands.py`) matched
`\\bbga ([a-z][a-z-]*)` and asked only whether the *word* names a
subcommand. Flags were unread except `blast`'s, so round 82's 63 long
flags across seven guides existed by luck. Here the line is tokenised
and handed to `create_parser().parse_known_args`, and a leftover is a
failure: that is the same object the shell reaches.

Subject and argument: only *fenced* lines are read, and only ones whose
first word is `bga` followed by whitespace - prose about `bga` is the
argument, and `bga/ingest/` is a path. `docs/backlog`, `docs/audits`
and `docs/spec` are excluded: a task file quoting the command a past
round ran is a record, and 41 of their 277 fenced lines name flags that
have since been renamed. Rewriting those would make them false.

UX-575's piped shape joins the sweep: a documented line that pipes is
run into a reader that stops, and must still exit 0.
"""
import contextlib
import io
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FIXTURE_RUN = REPO / "tests" / "fixtures" / "macro_micro" / "run"

# `docs/` less the three record trees, plus the two the older check
# never looked at at all.
SWEPT = [
    "README.md",
    "CHANGELOG.md",
    "examples",
    "docs/README.md",
    "docs/guides",
    "docs/contributing",
    "docs/design",
]

# A documented line is a command, not a shell script: everything from
# the first pipe/redirect/chain/comment belongs to the shell, not to bga.
_SHELL_TAIL = re.compile(r"\s(\||>>|>|&&|;|#)(\s|$)")

# `RUN`, `RUN/`, `RUN_DIRECTORY`, `A`, `B`, `TARGET`, `/path/to/…` - the
# stand-ins a guide writes where a run directory goes.
_PLACEHOLDER = re.compile(r"^([A-Z][A-Z0-9_]*/?|/path/to/[\w./-]+)$")


def _swept_files():
    files = []
    for entry in SWEPT:
        path = REPO / entry
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
        elif path.exists():
            files.append(path)
    return files


def _command_lines():
    """(path, line number, raw line, the bga command with its shell tail cut)."""
    for path in _swept_files():
        fenced = False
        for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if raw.strip().startswith("```"):
                fenced = not fenced
                continue
            if not fenced:
                continue
            text = raw.strip()
            if text.startswith("$ "):
                text = text[2:]
            if not re.match(r"^bga(\s|$)", text):
                continue
            cut = _SHELL_TAIL.search(text)
            command = (text[:cut.start()] if cut else text).rstrip("\\").strip()
            yield path, number, text, command


def _tokens(command: str, run_dir: str) -> list[str]:
    return [
        run_dir if _PLACEHOLDER.match(token) else token
        for token in shlex.split(command)
    ][1:]


def _refusal(tokens: list[str]) -> str | None:
    """What the real CLI would say about these arguments, or None."""
    from bga.cli import _schema_for, create_parser
    from bga.tools_dispatch import TOOL_ALIASES

    if not tokens:
        return None
    command = next((t for t in tokens if not t.startswith("-")), None)

    if "--schema" in tokens:
        # `--schema` is answered before argparse (UX-190), so the parser
        # is the wrong instrument for it - `_schema_for` is the right one.
        return None if _schema_for(command, tokens) else f"no schema for {command!r}"
    if command in TOOL_ALIASES:
        # A tool's own arguments are its business (UX-67): `bga extract`
        # never reaches this parser. The word is checked, not the flags.
        return None

    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            _, extras = create_parser().parse_known_args(tokens)
    except SystemExit as exit_:
        if not exit_.code:          # --help/--version print and leave
            return None
        said = err.getvalue().strip().splitlines()
        return said[-1] if said else "the parser exited non-zero"
    return f"unrecognized: {extras}" if extras else None


def test_every_documented_bga_line_parses(tmp_path):
    run_dir = str(tmp_path)
    offenders = []
    for path, number, text, command in _command_lines():
        try:
            tokens = _tokens(command, run_dir)
        except ValueError as exc:
            offenders.append(f"{path.relative_to(REPO)}:{number}: {text}\n    {exc}")
            continue
        refusal = _refusal(tokens)
        if refusal:
            offenders.append(f"{path.relative_to(REPO)}:{number}: {text}\n    {refusal}")

    assert offenders == [], (
        "documented `bga` line(s) the real parser refuses:\n  "
        + "\n  ".join(offenders)
    )


def test_the_sweep_reads_the_lines_it_claims_to():
    """A sweep over nothing passes. This is its population, counted."""
    lines = list(_command_lines())
    per_file = {path for path, _, _, _ in lines}

    assert len(lines) >= 150, len(lines)
    assert any(p.name == "cli.md" for p in per_file)
    assert any(p.name == "README.md" and p.parent == REPO for p in per_file)


def _piped_documented_lines():
    for path, number, text, command in _command_lines():
        if "|" in text and "--schema" in command:
            yield path, number, command


def test_a_documented_pipe_survives_a_reader_that_stops():
    """UX-575's shape, on the guides' own piped lines."""
    env = dict(os.environ)
    env.pop("PYTHONUNBUFFERED", None)   # or the deferred flush cannot happen
    env["PYTHONPATH"] = str(REPO)

    seen = 0
    for path, number, command in _piped_documented_lines():
        argv = _tokens(command, str(FIXTURE_RUN))
        proc = subprocess.Popen(
            [sys.executable, "-m", "bga.cli", *argv],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=REPO, env=env,
        )
        proc.stdout.close()
        stderr = proc.stderr.read()
        proc.stderr.close()
        code = proc.wait(timeout=120)
        seen += 1
        where = f"{path.relative_to(REPO)}:{number}: {command}"
        assert "Traceback" not in stderr, f"{where}\n{stderr}"
        assert "Exception ignored" not in stderr, f"{where}\n{stderr}"
        assert code == 0, f"{where} exited {code}: {stderr}"

    assert seen >= 3, seen


def test_the_guides_documented_analyze_pipe_runs():
    """`cli.md`'s own `bga analyze RUN/ --format json | head -2`."""
    env = dict(os.environ)
    env.pop("PYTHONUNBUFFERED", None)
    env["PYTHONPATH"] = str(REPO)
    proc = subprocess.Popen(
        [sys.executable, "-m", "bga.cli", "analyze", str(FIXTURE_RUN),
         "--format", "json"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=REPO, env=env,
    )
    first_two = [proc.stdout.readline() for _ in range(2)]
    proc.stdout.close()
    stderr = proc.stderr.read()
    proc.stderr.close()
    code = proc.wait(timeout=120)

    assert "analyze/v" in first_two[1], first_two
    assert "Traceback" not in stderr, stderr
    assert code == 0, stderr


def test_the_sweep_executes_only_operands_the_repository_ships():
    """A store this machine happens to have is not a repository fact.

    `examples/**/.bga/runs/` exists in this checkout and in no commit,
    so a sweep resolving a documented run directory against it would be
    green here and red on a fresh clone. Everything the sweep *executes*
    is either a `--schema` request - answered before any run directory
    or `@alias` is resolved (UX-190) - or the tracked `macro_micro`
    fixture. Every other documented line is parsed, never run.
    """
    listed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(FIXTURE_RUN.relative_to(REPO))],
        capture_output=True, text=True, cwd=REPO,
    )
    assert listed.returncode == 0, listed.stderr

    executed = [_tokens(c, str(FIXTURE_RUN)) for _, _, c in _piped_documented_lines()]
    executed.append(["analyze", str(FIXTURE_RUN), "--format", "json"])
    for argv in executed:
        assert ".bga" not in " ".join(argv), argv
        for token in argv:
            if token.startswith(("-", "@")) or "/" not in token:
                continue                      # a flag, an alias, a subcommand
            assert token.startswith(str(REPO / "tests" / "fixtures")), token
        assert "--schema" in argv or argv[1] == str(FIXTURE_RUN), argv


@pytest.mark.parametrize("root", SWEPT)
def test_every_swept_root_exists(root):
    """A root that was renamed away silently empties the sweep."""
    assert (REPO / root).exists(), root
