"""UX-1067: the archive and its manifest carry no original metadata.

`tarfile.add()` copies the source's mtime, uid, gid, uname and gname
into every header, and `bundle.export()`'s manifest carries the
snapshot's `stamp` and `packed_at` (`anonymized-bundle.md` 6.9).
`export_anonymized()` builds each header from scratch and pseudonymizes
or drops the manifest fields that name a machine or a capture. Member
contents are `UX-1062`'s guard; the members here are the least that
clears its disclosure policy.
"""
import os
import tarfile

import pytest

from bga import anonymize, bundle, run_store

STAMP = "20260902T101112Z"
NAMED_UID = 4242
NAMED_GID = 4242


def _write(root, relative, text):
    path = os.path.join(root, relative)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


@pytest.fixture
def project(tmp_path):
    _write(str(tmp_path), "project.conf", "name: demo\n")
    return str(tmp_path)


@pytest.fixture
def snapshot(project):
    path = os.path.join(run_store.runs_dir(project), STAMP)
    _write(path, "run/graph.json", '{"elements": [{"uid": "app.bst"}]}')
    _write(path, "run/trace.json", '{"spans": []}')
    _write(path, "run/run-context.json", '{"host": "runner-7"}')
    _write(path, "run/sources.json", '{"schema": "sources/v1", "elements": {}}')
    _write(path, "plane2.json", '{"process_count": 1}')
    return path


def _yes(_screen):
    return True


@pytest.fixture
def key_and_map(project):
    key = anonymize.load_or_create_key(project)
    pmap = anonymize.PseudonymMap.for_project(project)
    return key, pmap


def test_the_anonymized_archive_and_manifest_carry_no_original_metadata(
        snapshot, key_and_map, tmp_path, monkeypatch):
    key, pmap = key_and_map
    # `tarfile.add()` would stamp the *real* mtime/uid/gid of the files
    # this test wrote; overriding `TarInfo.gettarinfo` proves the
    # anonymized path never calls it, rather than merely matching by luck.
    real_gettarinfo = tarfile.TarFile.gettarinfo

    def poisoned_gettarinfo(self, *args, **kwargs):
        info = real_gettarinfo(self, *args, **kwargs)
        info.mtime = 1_700_000_000
        info.uid, info.gid = NAMED_UID, NAMED_GID
        info.uname, info.gname = "alice", "alice"
        return info

    monkeypatch.setattr(tarfile.TarFile, "gettarinfo", poisoned_gettarinfo)

    destination = str(tmp_path / "anon.tar.gz")
    path, manifest = bundle.export_anonymized(snapshot, key, pmap, destination, approve=_yes)

    assert path == destination
    assert manifest["stamp"] != STAMP
    assert "packed_at" not in manifest
    assert manifest["key_fingerprint"] == anonymize.key_fingerprint(key)

    with tarfile.open(path, mode="r:gz") as archive:
        infos = archive.getmembers()
    assert infos, "the archive packed no members"
    for info in infos:
        assert info.mtime == 0
        assert info.uid == 0 and info.gid == 0
        assert info.uname == "" and info.gname == ""
        assert STAMP not in info.name


def test_the_default_anonymized_name_carries_no_stamp(
        snapshot, key_and_map, tmp_path, monkeypatch):
    key, pmap = key_and_map
    monkeypatch.chdir(tmp_path)
    path, _manifest = bundle.export_anonymized(snapshot, key, pmap, approve=_yes)
    assert STAMP not in os.path.basename(path)
    assert os.path.basename(path) == bundle.anonymized_output()


#: gzip header: magic, method, flags, mtime(4), extra flags, OS.
_FNAME_BIT = 0x08


def test_the_gzip_header_carries_no_file_name(snapshot, key_and_map, tmp_path):
    """`gzip.GzipFile` writes FNAME from `fileobj.name` unless told not to
    (`filename=""`); an output named after the owner or their machine
    would otherwise travel inside the gzip header itself, ahead of and
    outside anything the tar layer or the manifest transform touches."""
    key, pmap = key_and_map
    private_name = "acme-corp-alice-laptop-capture.tar.gz"
    destination = str(tmp_path / private_name)
    path, _manifest = bundle.export_anonymized(snapshot, key, pmap, destination, approve=_yes)

    with open(path, "rb") as handle:
        header = handle.read(10)
        rest = handle.read()

    assert header[:2] == b"\x1f\x8b", "not a gzip stream"
    flags = header[3]
    mtime = int.from_bytes(header[4:8], "little")
    assert not flags & _FNAME_BIT, "FNAME bit set in gzip flags"
    assert mtime == 0
    assert b"acme-corp-alice-laptop-capture" not in header + rest
