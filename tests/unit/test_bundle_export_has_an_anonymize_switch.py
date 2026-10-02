"""UX-1295: `bga bundle --export STAMP --anonymize` asks on a terminal,
refuses without one, and writes nothing, map included, unless approved."""

import io
import json
import os
import pathlib
import shutil
import stat

import pytest

from bga import bundle, cli, run_store

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "macro_micro"
STAMP = "20260902T101112Z"


class _Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


def _project(tmp_path: pathlib.Path, cpu_model=None) -> pathlib.Path:
    project = tmp_path / "project"
    snapshot = pathlib.Path(run_store.runs_dir(str(project))) / STAMP
    shutil.copytree(FIXTURE / "run", snapshot / "run")
    shutil.copyfile(FIXTURE / "plane2.json", snapshot / "plane2.json")
    (project / "project.conf").write_text("name: p\n")
    if cpu_model:
        context = snapshot / "run" / "run-context.json"
        document = json.loads(context.read_text(encoding="utf-8"))
        document["host_manifest"]["cpu_model"] = cpu_model
        context.write_text(json.dumps(document), encoding="utf-8")
    return project


def _run(monkeypatch, cwd, stdin, *argv) -> int:
    monkeypatch.chdir(cwd)
    monkeypatch.setattr("sys.stdin", stdin)
    return cli.cmd_bundle(cli.create_parser().parse_args(["bundle", *argv]))


def _anon(project: pathlib.Path) -> pathlib.Path:
    return project / ".bga" / "anon"


def _mode(path: pathlib.Path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def test_y_on_a_terminal_writes_a_clean_bundle_that_loads(tmp_path, monkeypatch, capsys):
    project = _project(tmp_path)
    out = tmp_path / "share.bga-bundle.tar.gz"
    code = _run(monkeypatch, project, _Terminal("y\n"), "--export", "@last", "--anonymize", "-o", str(out))
    printed = capsys.readouterr().out
    assert code == 0 and out.is_file(), printed
    assert "residue scan: clean" in printed and f"Wrote {out}" in printed
    assert _mode(_anon(project) / "key") == _mode(_anon(project) / "map.json") == 0o600
    graph = json.loads((FIXTURE / "run" / "graph.json").read_text(encoding="utf-8"))
    dictionary = bundle.residue_dictionary({e["uid"] for e in graph["elements"]} | {STAMP})
    assert len(dictionary) > 5 and bundle.residue(str(out), dictionary) == []
    fingerprint = bundle.read_manifest(str(out))["key_fingerprint"]
    assert f"--resolve --key-fingerprint {fingerprint}" in printed
    far = tmp_path / "far"
    far.mkdir()
    (far / "project.conf").write_text("name: far\n")
    assert _run(monkeypatch, far, io.StringIO(""), "--load", str(out)) == 0
    [loaded] = os.listdir(run_store.runs_dir(str(far)))
    assert loaded != STAMP and (pathlib.Path(run_store.runs_dir(str(far))) / loaded / "run" / "graph.json").is_file()


@pytest.mark.parametrize("stdin", [_Terminal("n\n"), _Terminal(""), io.StringIO("y\n")], ids=["n", "eof", "no-tty"])
def test_no_approval_writes_nothing(stdin, tmp_path, monkeypatch, capsys):
    project = _project(tmp_path)
    out = tmp_path / "share.bga-bundle.tar.gz"
    code = _run(monkeypatch, project, stdin, "--export", "@last", "--anonymize", "-o", str(out))
    printed = capsys.readouterr()
    assert code == 2 and "did not approve" in printed.err
    assert "kept verbatim" in printed.out and "residue scan: clean" in printed.out
    assert ("not a terminal" in printed.err) == (not stdin.isatty())
    assert sorted(os.listdir(tmp_path)) == ["project"]
    assert not (_anon(project) / "map.json").exists()


def test_a_planted_name_refuses_whatever_the_answer(tmp_path, monkeypatch, capsys):
    project = _project(tmp_path, cpu_model="Xeon lib-a.bst edition")
    out = tmp_path / "share.bga-bundle.tar.gz"
    code = _run(monkeypatch, project, _Terminal("y\n"), "--export", "@last", "--anonymize", "-o", str(out))
    printed = capsys.readouterr()
    assert code == 2 and "residue scan found original names" in printed.err and "lib-a" in printed.err
    assert "Write this bundle?" not in printed.out
    assert sorted(os.listdir(tmp_path)) == ["project"]
    assert not (_anon(project) / "map.json").exists()


@pytest.mark.parametrize(
    "argv",
    [["--load", "x.tar.gz"], ["--resolve", "--key-fingerprint", "ab"], ["--export", "@last", "--no-plane2"]],
    ids=["load", "resolve", "no-plane2"],
)
def test_anonymize_with_another_mode_is_a_usage_error(argv, tmp_path, monkeypatch, capsys):
    project = _project(tmp_path)
    assert _run(monkeypatch, project, _Terminal("y\n"), *argv, "--anonymize") == 2
    assert "--anonymize goes with --export alone" in capsys.readouterr().err
    assert not _anon(project).exists()


def test_the_help_names_the_switch():
    text = cli.create_parser()._subparsers._group_actions[0].choices["bundle"].format_help()
    assert "--anonymize" in text and "[--anonymize]" in text
