"""UX-900: CI keeps bundles in build-number directories; `bga` reads that tree as a store.

`bga bundle --load DIR` materialises it, idempotently; `bga snapshot
--list|--aggregate|--capacity --bundles DIR` reads it in place. Both go
through `bundle.load_tree`, which checks every bundle before writing any.
"""

import hashlib
import io
import json
import os
import pathlib
import shutil
import tarfile

import pytest

from bga import bundle, run_store

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures"
RUNS = {
    "20260901T100000Z": FIXTURES / "same_build_twice_cold" / "run",
    "20260902T100000Z": FIXTURES / "same_build_twice_incremental" / "run",
}
THIRD_STAMP = "20260903T100000Z"


def _project(root: pathlib.Path) -> str:
    root.mkdir(parents=True, exist_ok=True)
    (root / "project.conf").write_text("name: demo\n")
    return str(root)


def _snapshot(project: str, stamp: str, run: pathlib.Path) -> str:
    path = os.path.join(run_store.runs_dir(project), stamp)
    shutil.copytree(run, os.path.join(path, run_store.RUN_SUBDIR))
    return path


@pytest.fixture
def home(tmp_path):
    """The two runs as a store, exported into a CI-shaped tree beside one stray file."""
    project = _project(tmp_path / "home")
    tree = tmp_path / "ci"
    for number, (stamp, run) in enumerate(RUNS.items(), start=100):
        snapshot = _snapshot(project, stamp, run)
        (tree / str(number)).mkdir(parents=True)
        bundle.export(snapshot, str(tree / str(number) / bundle.default_output(stamp)))
    (tree / "100" / "console.log").write_text("not a bundle\n")
    return project, str(tree)


def _truncated(data: bytes) -> bytes:
    return data[: len(data) // 2]


def _manifest_edited(edit):
    """Rewrite the archive with `edit` applied to its manifest - how a newer or lying bundle is forged."""

    def forge(data: bytes) -> bytes:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as original:
            entries = [(info, original.extractfile(info).read()) for info in original.getmembers()]
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode="w:gz") as archive:
            for info, payload in entries:
                if info.name == bundle.MANIFEST_NAME:
                    manifest = json.loads(payload)
                    edit(manifest)
                    payload = json.dumps(manifest).encode("utf-8")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
        return out.getvalue()

    return forge


BAD = {
    "truncated": _truncated,
    # check_readable's refusal: a manifest schema this bga does not read.
    "newer": _manifest_edited(lambda m: m.update(schema="bundle-manifest/v99")),
    # _safe_members' refusal: the manifest names a member the archive lacks.
    "short": _manifest_edited(lambda m: m["members"].append({"path": "run/extra.json", "bytes": 1})),
}


def _a_bad_third(tmp_path, tree: str, kind: str) -> str:
    """A third bundle, sorted last so a loader without the pre-pass would already have written two."""
    scratch = _project(tmp_path / "scratch")
    snapshot = _snapshot(scratch, THIRD_STAMP, RUNS["20260901T100000Z"])
    whole = bundle.export(snapshot, str(tmp_path / "whole.tar.gz"))[0]
    target = os.path.join(tree, "102", bundle.default_output(THIRD_STAMP))
    os.makedirs(os.path.dirname(target))
    pathlib.Path(target).write_bytes(BAD[kind](pathlib.Path(whole).read_bytes()))
    return target


def _store_digest(project: str) -> dict:
    root = run_store.runs_dir(project)
    out = {}
    for directory, _subdirs, files in os.walk(root):
        for name in files:
            path = os.path.join(directory, name)
            out[os.path.relpath(path, root)] = hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
    return out


def _masked(document: dict) -> dict:
    """The document with its project root cut off every path it names."""
    root = document["project"]

    def walk(node):
        if isinstance(node, dict):
            return {key: walk(value) for key, value in node.items()}
        if isinstance(node, list):
            return [walk(value) for value in node]
        if isinstance(node, str) and node.startswith(root):
            return "<project>" + node[len(root) :]
        return node

    return walk(document)


def _snapshot_main(capsys, argv) -> tuple[int, str, str]:
    from tools.bga_snapshot import main

    capsys.readouterr()
    code = main(argv)
    out, err = capsys.readouterr()
    return code, out, err


class TestReadInPlace:
    def test_list_shows_the_two_runs_and_ignores_the_stray_file(self, home, capsys):
        _project_dir, tree = home
        code, out, err = _snapshot_main(capsys, ["--list", "--bundles", tree])
        assert code == 0, err
        assert out.splitlines()[0] == f"2 snapshots in {tree}:"
        assert all(stamp in out for stamp in RUNS)

    def test_aggregate_equals_the_run_directories_but_for_paths(self, home, capsys):
        project, tree = home
        code, direct, err = _snapshot_main(capsys, ["--project", project, "--aggregate", "--format", "json"])
        assert code == 0, err
        code, bundled, err = _snapshot_main(capsys, ["--aggregate", "--format", "json", "--bundles", tree])
        assert code == 0, err
        assert _masked(json.loads(bundled)) == _masked(json.loads(direct))

    def test_the_copy_is_gone_on_exit(self, home, capsys, monkeypatch, tmp_path):
        _project_dir, tree = home
        scratch = tmp_path / "tmpdir"
        scratch.mkdir()
        monkeypatch.setenv("TMPDIR", str(scratch))
        monkeypatch.setattr("tempfile.tempdir", None)
        assert _snapshot_main(capsys, ["--list", "--bundles", tree])[0] == 0
        assert list(scratch.iterdir()) == []


class TestOneRefusal:
    @pytest.mark.parametrize("kind", sorted(BAD))
    def test_a_bad_bundle_is_named_and_nothing_is_written(self, home, tmp_path, kind):
        _project_dir, tree = home
        bad = _a_bad_third(tmp_path, tree, kind)
        far = _project(tmp_path / "far")
        with pytest.raises(bundle.BundleError) as refused:
            bundle.load_tree(tree, far)
        assert bad in str(refused.value)
        assert not os.path.exists(run_store.runs_dir(far))

    def test_the_in_place_reader_refuses_it_too(self, home, tmp_path, capsys):
        _project_dir, tree = home
        truncated = _a_bad_third(tmp_path, tree, "truncated")
        code, out, err = _snapshot_main(capsys, ["--list", "--bundles", tree])
        assert code == 2 and truncated in err and out == ""


class TestMaterialise:
    def test_loading_the_tree_twice_leaves_the_same_store(self, home, tmp_path):
        _project_dir, tree = home
        far = _project(tmp_path / "far")
        bundle.load_tree(tree, far)
        first = _store_digest(far)
        bundle.load_tree(tree, far)
        assert _store_digest(far) == first
        assert [os.path.basename(p) for p in run_store.list_snapshots(far)] == list(RUNS)

    def test_bga_bundle_load_takes_a_directory(self, home, tmp_path, monkeypatch, capsys):
        from bga.cli import main

        _project_dir, tree = home
        far = _project(tmp_path / "far")
        monkeypatch.chdir(far)
        assert main(["bundle", "--load", tree]) == 0
        assert capsys.readouterr().out.splitlines()[0].startswith("Loaded 2 bundles from ")
        assert [os.path.basename(p) for p in run_store.list_snapshots(far)] == list(RUNS)
