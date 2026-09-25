"""UX-1011: `--jobserver` paid three `bst show` subprocesses (max-jobs,
kinds, auth map), each ~2s of BuildStream startup - Graviton run
36123209379: `off` wall 21-23s, `auto` 28s, all before the traced build
starts (`auto`'s "Compiling the trace hook..." at 8.9s against `off`'s
2.8s). `read_jobserver_metadata_for_build` is `main`'s own site for the
read; this counts the `bst show` calls it makes, via a fake `bst` that
logs its own argv - no real `bst`/`bwrap` needed."""
import stat

from tools.bst_native_build_tracer import read_jobserver_metadata_for_build

_FAKE_BST = """#!/bin/sh
echo "$@" >> "$FAKE_BST_ARGV_FILE"
echo "core.bst cmake"
"""


def _fake_bst(tmp_path, monkeypatch):
    script = tmp_path / "bst"
    script.write_text(_FAKE_BST)
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    argv_file = tmp_path / "argv.txt"
    monkeypatch.setenv("FAKE_BST_ARGV_FILE", str(argv_file))
    return str(script), argv_file


def test_the_jobserver_path_pays_one_bst_show_call(tmp_path, monkeypatch):
    script, argv_file = _fake_bst(tmp_path, monkeypatch)

    read_jobserver_metadata_for_build(
        str(tmp_path), [script, "build", "t.bst"], jobserver=4)

    show_calls = [line for line in argv_file.read_text().splitlines()
                 if "show" in line]
    assert len(show_calls) == 1


def test_no_jobserver_reads_nothing(tmp_path, monkeypatch):
    script, argv_file = _fake_bst(tmp_path, monkeypatch)

    result = read_jobserver_metadata_for_build(
        str(tmp_path), [script, "build", "t.bst"], jobserver=None)

    assert result == (None, None, None, {}, {}, {})
    assert not argv_file.exists()
