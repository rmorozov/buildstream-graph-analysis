"""UX-1291: every command in `sharing-a-capture.md` runs, in order, on committed fixtures.

The guide's `bash` blocks are read, not copied: a runner project holds
`same_build_twice_cold` and `macro_micro` as two snapshots, a reading
machine gets the `ci` tree the guide writes, and each line must exit 0.
"""

import contextlib
import io
import json
import os
import pathlib
import re
import shlex
import shutil

import pytest

from bga import run_store
from bga.cli import main

REPO = pathlib.Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs/guides/sharing-a-capture.md"
FIXTURES = REPO / "tests/fixtures"
SNAPSHOTS = (
    ("20260901T100000Z", FIXTURES / "same_build_twice_cold/run", None),
    ("20260902T101112Z", FIXTURES / "macro_micro/run", FIXTURES / "macro_micro/plane2.json"),
)
#: The flags that read a tree on the reading machine; every other line runs where the capture and key are.
READS_THE_TREE = ("--load", "--bundles")
#: One per step, so a step whose command left the guide is red here, not silent.
STEPS = ("--export", "--anonymize", "--load", "--bundles", "--resolve")


class _Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


def _commands() -> list:
    blocks = re.findall(r"^```bash\n(.*?)^```", GUIDE.read_text(encoding="utf-8"), re.M | re.S)
    return [line.strip() for block in blocks for line in block.splitlines() if line.strip()]


def _project(path: pathlib.Path, snapshots=()) -> pathlib.Path:
    path.mkdir(parents=True)
    (path / "project.conf").write_text("name: demo\n")
    for stamp, run, plane2 in snapshots:
        snapshot = pathlib.Path(run_store.runs_dir(str(path))) / stamp
        shutil.copytree(run, snapshot / "run")
        if plane2:
            shutil.copyfile(plane2, snapshot / "plane2.json")
    return path


def _bga(monkeypatch, cwd, argv, stdin) -> tuple:
    monkeypatch.chdir(cwd)
    monkeypatch.setattr("sys.stdin", stdin)
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        try:
            code = main(argv)
        except SystemExit as raised:
            code = raised.code
        except Exception as raised:  # a traceback is a failed line, reported with the rest
            code = repr(raised)
    return code or 0, sink.getvalue()


@pytest.fixture
def walked(tmp_path, monkeypatch):
    """`[(line, exit, output)]` for every line of the guide, run in order."""
    runner = _project(tmp_path / "runner", SNAPSHOTS)
    reader = _project(tmp_path / "reader")
    env = {}
    ran = []
    for line in _commands():
        words = shlex.split(line)
        if words[:2] == ["mkdir", "-p"]:
            os.makedirs(runner / words[2], exist_ok=True)
            ran.append((line, 0, ""))
            continue
        stdin = _Terminal("y\n")
        if words[0] == "cat" and words[2] == "|":
            pseudonym = next((k for k, v in _map(runner).items() if v.startswith("element\0")), "e-none")
            (runner / words[1]).write_text(f"rebuild {pseudonym} first\n")
            stdin, words = io.StringIO((runner / words[1]).read_text()), words[3:]
        assert words[0] == "bga", f"the guide runs something this guard cannot: {line!r}"
        words = [env.get(word[1:], word) if word.startswith("$") else word for word in words]
        cwd = runner
        if any(flag in words for flag in READS_THE_TREE):
            shutil.rmtree(reader / "ci", ignore_errors=True)
            if (runner / "ci").is_dir():
                shutil.copytree(runner / "ci", reader / "ci")
            cwd = reader
        code, out = _bga(monkeypatch, cwd, words[1:], stdin)
        found = re.search(r"--key-fingerprint (\w+)", out)
        if found:
            env["FINGERPRINT"] = found.group(1)
        ran.append((line, code, out))
    return ran


def _map(project: pathlib.Path) -> dict:
    path = project / ".bga/anon/map.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


class TestTheGuideRuns:
    def test_every_command_exits_zero(self, walked):
        failed = [(line, code, out[-400:]) for line, code, out in walked if code != 0]
        assert failed == [], f"guide command(s) that did not exit 0: {failed}"

    def test_each_step_has_its_command(self):
        lines = " ".join(_commands())
        missing = [flag for flag in STEPS if flag not in lines]
        assert missing == [], f"step(s) with no command in the guide: {missing}"

    def test_the_steps_do_what_the_guide_says(self, walked):
        out = {line: text for line, _code, text in walked}
        [export] = [t for line, t in out.items() if "--export" in line and "--anonymize" not in line]
        [anon] = [t for line, t in out.items() if "--anonymize" in line]
        [load] = [t for line, t in out.items() if "--load" in line]
        [listed] = [t for line, t in out.items() if "--bundles" in line]
        [resolved] = [t for line, t in out.items() if "--resolve" in line]
        assert "Wrote ci/101/run.bga-bundle.tar.gz" in export
        assert "residue scan: clean" in anon and "Wrote share.bga-bundle.tar.gz" in anon
        assert "Loaded 1 bundle from ci" in load and "1 snapshot in ci" in listed
        assert re.search(r"rebuild lib-\w+ first", resolved), resolved

    def test_the_key_is_kept_0600(self, walked, tmp_path):
        anon = tmp_path / "runner/.bga/anon"
        modes = {name: oct(os.stat(anon / name).st_mode & 0o777) for name in ("key", "map.json")}
        assert modes == {"key": "0o600", "map.json": "0o600"}
