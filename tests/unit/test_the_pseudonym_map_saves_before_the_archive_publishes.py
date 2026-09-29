"""UX-1086: the map publishes atomically, and before the archive does.

`export_anonymized` must not leave a published bundle with a corrupt or
truncated map: the map is written to a temp file, fsynced, and renamed
onto the real path *before* the archive's own rename onto the
destination. An injected failure during the map write must leave both
the destination and the prior map untouched.
"""

import json
import os
import pathlib
import stat

import pytest

from bga import anonymize, bundle, run_store

FIXTURES = pathlib.Path(__file__).resolve().parents[2] / "tests" / "fixtures"
STAMP = "20260902T101112Z"
KEY = bytes(range(32))
RUN_FILES = ("graph.json", "trace.json", "run-context.json", "sources.json")
BESIDE_FILES = ("plane2.json", "host-samples.jsonl")
FIXTURE = "macro_micro"


def _source(name: str) -> pathlib.Path:
    root = FIXTURES / FIXTURE
    return next((p for p in (root / "run" / name, root / name) if p.is_file()), root / name)


def _snapshot(project: pathlib.Path) -> str:
    snapshot = pathlib.Path(run_store.runs_dir(str(project))) / STAMP
    (snapshot / "run").mkdir(parents=True)
    for name in RUN_FILES + BESIDE_FILES:
        source = _source(name)
        if source.is_file():
            target = snapshot / ("run" if name in RUN_FILES else "") / name
            target.write_bytes(source.read_bytes())
    return str(snapshot)


def _export(tmp_path, pmap, destination):
    project = tmp_path / "project"
    snapshot = _snapshot(project)
    return bundle.export_anonymized(snapshot, KEY, pmap, destination, approve=lambda screen: True)


def test_an_injected_map_write_failure_leaves_no_archive_and_the_prior_map_intact(tmp_path, monkeypatch):
    map_path = tmp_path / "anon" / "map.json"
    map_path.parent.mkdir(parents=True)
    prior = json.dumps({"e-oldtoken": "element\0keep-me"}, indent=2, sort_keys=True).encode("utf-8")
    map_path.write_bytes(prior)
    os.chmod(map_path, 0o600)

    pmap = anonymize.PseudonymMap(str(map_path))
    destination = tmp_path / "out.tar.gz"

    real_replace = os.replace

    def failing_replace(src, dst, *args, **kwargs):
        if str(dst) == str(map_path):
            raise OSError("injected map-write failure")
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", failing_replace)

    with pytest.raises(OSError, match="injected map-write failure"):
        _export(tmp_path, pmap, str(destination))

    assert not destination.exists()
    assert map_path.read_bytes() == prior
    assert stat.S_IMODE(os.stat(map_path).st_mode) == 0o600


def test_a_normal_export_publishes_the_map_then_the_archive(tmp_path, monkeypatch):
    map_path = tmp_path / "anon" / "map.json"
    pmap = anonymize.PseudonymMap(str(map_path))
    destination = tmp_path / "out.tar.gz"

    order = []
    real_replace = os.replace

    def recording_replace(src, dst, *args, **kwargs):
        order.append(str(dst))
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", recording_replace)

    path, _manifest = _export(tmp_path, pmap, str(destination))

    assert path == str(destination)
    assert destination.exists()
    assert map_path.exists()
    assert stat.S_IMODE(os.stat(map_path).st_mode) == 0o600
    map_index = next(i for i, d in enumerate(order) if d == str(map_path))
    archive_index = next(i for i, d in enumerate(order) if d == str(destination))
    assert map_index < archive_index

    assert json.loads(map_path.read_text(encoding="utf-8"))


def test_an_injected_write_failure_leaves_no_temp_file_and_the_prior_map_intact(tmp_path, monkeypatch):
    map_path = tmp_path / "anon" / "map.json"
    map_path.parent.mkdir(parents=True)
    prior = json.dumps({"e-oldtoken": "element\0keep-me"}, indent=2, sort_keys=True).encode("utf-8")
    map_path.write_bytes(prior)
    os.chmod(map_path, 0o600)

    pmap = anonymize.PseudonymMap(str(map_path))
    destination = tmp_path / "out.tar.gz"

    real_write = os.write

    def failing_write(fd, data):
        path = os.readlink(f"/proc/self/fd/{fd}")
        if str(map_path) in path and ".tmp-" in path:
            raise OSError("injected write failure")
        return real_write(fd, data)

    monkeypatch.setattr(os, "write", failing_write)

    with pytest.raises(OSError, match="injected write failure"):
        _export(tmp_path, pmap, str(destination))

    assert not destination.exists()
    assert map_path.read_bytes() == prior
    assert list(map_path.parent.glob("*.tmp-*")) == []


def test_an_injected_map_write_failure_leaves_an_existing_destination_unchanged(tmp_path, monkeypatch):
    map_path = tmp_path / "anon" / "map.json"
    map_path.parent.mkdir(parents=True)
    prior = json.dumps({"e-oldtoken": "element\0keep-me"}, indent=2, sort_keys=True).encode("utf-8")
    map_path.write_bytes(prior)
    os.chmod(map_path, 0o600)

    pmap = anonymize.PseudonymMap(str(map_path))
    destination = tmp_path / "out.tar.gz"
    existing = b"a previously published bundle's bytes"
    destination.write_bytes(existing)

    real_replace = os.replace

    def failing_replace(src, dst, *args, **kwargs):
        if str(dst) == str(map_path):
            raise OSError("injected map-write failure")
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", failing_replace)

    with pytest.raises(OSError, match="injected map-write failure"):
        _export(tmp_path, pmap, str(destination))

    assert destination.read_bytes() == existing
    assert map_path.read_bytes() == prior
