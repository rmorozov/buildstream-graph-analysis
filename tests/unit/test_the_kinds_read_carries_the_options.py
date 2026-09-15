"""UX-870: `read_element_kinds_for_jobserver` forwards the user's own
`bst` global options and says why it failed, instead of dropping
everything but `cmd[0]` and one target. A fake `bst` script on disk
records its own argv; no real `bst`/`bwrap` needed."""
import json
import stat

import pytest

from tools.bst_native_build_tracer import (
    _bst_global_options,
    _write_kinds_read,
    jobserver_kinds_warning,
    read_element_kinds_for_jobserver,
)

_FAKE_BST = """#!/bin/sh
echo "$@" >> "$FAKE_BST_ARGV_FILE"
if [ -n "$FAKE_BST_EXIT" ]; then
    echo "boom" >&2
    exit "$FAKE_BST_EXIT"
fi
if [ -n "$FAKE_BST_EMPTY" ]; then
    exit 0
fi
echo "core.bst cmake"
echo "toolchain.bst import"
"""


@pytest.fixture
def fake_bst(tmp_path, monkeypatch):
    script = tmp_path / "bst"
    script.write_text(_FAKE_BST)
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    argv_file = tmp_path / "argv.txt"
    monkeypatch.setenv("FAKE_BST_ARGV_FILE", str(argv_file))
    monkeypatch.delenv("FAKE_BST_EXIT", raising=False)
    monkeypatch.delenv("FAKE_BST_EMPTY", raising=False)
    return str(script)


def test_global_options_and_their_values_precede_show(fake_bst, tmp_path):
    cmd = [fake_bst, "-o", "arch", "x86_64", "--config", "c.yml", "build", "t.bst"]
    kinds, diag = read_element_kinds_for_jobserver(str(tmp_path), cmd)
    assert diag["argv"] == [fake_bst, "-o", "arch", "x86_64", "--config", "c.yml",
                            "show", "--format", "%{name} %{kind}", "t.bst"]
    assert kinds == {"core.bst": "cmake", "toolchain.bst": "import"}
    assert diag == {"argv": diag["argv"], "count": 2}


def test_options_after_the_subcommand_do_not_leak_into_show(fake_bst, tmp_path):
    # `--retry-failed` is a real `bst build` flag (zero values), chosen
    # over the task's own `--deps all` example so the target itself
    # (`_cmd_target`'s pre-existing scan, unchanged here) is unambiguous.
    cmd = [fake_bst, "build", "--retry-failed", "t.bst"]
    _kinds, diag = read_element_kinds_for_jobserver(str(tmp_path), cmd)
    assert diag["argv"] == [fake_bst, "show", "--format", "%{name} %{kind}", "t.bst"]
    assert "--retry-failed" not in diag["argv"]


def test_no_target_runs_with_no_target_argument(fake_bst, tmp_path):
    cmd = [fake_bst, "build"]
    kinds, diag = read_element_kinds_for_jobserver(str(tmp_path), cmd)
    assert diag["argv"] == [fake_bst, "show", "--format", "%{name} %{kind}"]
    assert kinds == {"core.bst": "cmake", "toolchain.bst": "import"}


def test_no_subcommand_at_all_is_no_target_without_running(tmp_path):
    opts, found = _bst_global_options([  "bst", "--no-colors", "--strict"])
    assert (opts, found) == (["--no-colors", "--strict"], False)
    kinds, diag = read_element_kinds_for_jobserver(
        str(tmp_path), ["bst", "--no-colors", "--strict"])
    assert kinds is None
    assert diag == {"argv": None, "returncode": None, "stderr_tail": "",
                    "reason": "no-target"}


def test_a_nonzero_exit_writes_the_reason_and_stderr_tail(fake_bst, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_BST_EXIT", "2")
    cmd = [fake_bst, "build", "t.bst"]
    kinds, diag = read_element_kinds_for_jobserver(str(tmp_path), cmd)
    assert kinds is None
    assert diag["reason"] == "exit"
    assert diag["returncode"] == 2
    assert "boom" in diag["stderr_tail"]

    bind_dir = tmp_path / "bind"
    bind_dir.mkdir()
    warning = _write_kinds_read(str(bind_dir), 4, kinds, diag)
    written = json.loads((bind_dir / "kinds_read.json").read_text())
    assert written == diag
    assert warning is not None
    assert "exit" in warning and str(bind_dir / "kinds_read.json") in warning


def test_empty_stdout_is_no_lines(fake_bst, tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_BST_EMPTY", "1")
    cmd = [fake_bst, "build", "t.bst"]
    kinds, diag = read_element_kinds_for_jobserver(str(tmp_path), cmd)
    assert kinds is None
    assert diag["reason"] == "no-lines"


def test_a_success_file_records_argv_and_count(fake_bst, tmp_path):
    cmd = [fake_bst, "build", "t.bst"]
    kinds, diag = read_element_kinds_for_jobserver(str(tmp_path), cmd)
    bind_dir = tmp_path / "bind"
    bind_dir.mkdir()
    warning = _write_kinds_read(str(bind_dir), 4, kinds, diag)
    written = json.loads((bind_dir / "kinds_read.json").read_text())
    assert written == {"argv": diag["argv"], "count": 2}
    assert warning is None  # kinds resolved - jobserver_kinds_warning says nothing


def test_the_warning_names_the_reason_and_the_path():
    diagnostic = {"argv": ["bst", "show"], "returncode": 2,
                 "stderr_tail": "boom", "reason": "exit"}
    line = jobserver_kinds_warning(4, None, diagnostic, "/tmp/x/kinds_read.json")
    assert line.startswith("Warning:") and "exit" in line
    assert "/tmp/x/kinds_read.json" in line


def test_two_value_option_consumes_both_its_tokens():
    opts, found = _bst_global_options(["bst", "-o", "k", "v", "build", "t.bst"])
    assert (opts, found) == (["-o", "k", "v"], True)


def test_a_bare_flag_before_the_subcommand_consumes_no_value():
    opts, found = _bst_global_options(["bst", "--no-strict", "build", "t.bst"])
    assert (opts, found) == (["--no-strict"], True)


def test_every_valued_option_of_the_installed_bst_consumes_its_values():
    """The arity table is read off the installed `cli` group, so the
    group is what checks it - a bst release that adds a valued global
    option reds here before it swallows a subcommand."""
    cli = pytest.importorskip("buildstream._frontend.cli")
    valued = [(opt, param.nargs) for param in cli.cli.params
              if not getattr(param, "is_flag", False) and param.nargs > 0
              for opt in param.opts]
    assert valued, "the installed cli group defines no valued option"
    wrong = []
    for opt, nargs in valued:
        values = [f"v{i}" for i in range(nargs)]
        got = _bst_global_options(["bst", opt, *values, "build", "t.bst"])
        if got != ([opt, *values], True):
            wrong.append((opt, got))
    assert wrong == [], wrong
