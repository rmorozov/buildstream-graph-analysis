"""UX-520: the capture travels whole, or the far side refuses it.

`run/` is not the capture. The analysis half was already portable — a
run directory copied to an unrelated path analyses fine — so the defect
was never portability: it was that a user who tars `run/`, the directory
every command's help names, carries Plane 1 and leaves the Plane 2
report, the raw trace, the host samples and the published analysis
behind.

The guards below hold the two halves of that. The pack side is *derived*
from `UX-381`'s `CAPTURE_LAYOUT` rather than listed here, so a member
added to the contract is bundled by existing and a guard that listed
seven names could not have noticed the eighth. The load side refuses
instead of half-reading, which is what the per-member contract version
buys: a bundle from a newer `bga` is recognised, named and declined with
nothing written.
"""
import gzip
import io
import json
import os
import tarfile

import pytest

from bga import bundle, run_store

STAMP = "20260902T101112Z"

# What a capture holds, one file per layout row that is not DERIVED.
# Contents are placeholders - every guard here is about which files move
# and what the manifest says about them, not about what they parse to.
CAPTURE = {
    "run/graph.json": '{"schema": "graph/v9"}',
    "run/trace.json": '{"schema": "trace/v9"}',
    "run/run-context.json": '{"schema": "run-context/v9", "host": {"id": "runner-7"}}',
    "run/sources.json": '{"schema": "sources/v1"}',
    "plane2.json": '{"schema": "plane2/v3"}',
    "plane2-resource.json": '{"cpu": 8}',
    "host-samples.jsonl": '{"schema": "host-samples/v1"}\n',
    "analyze.json": '{"schema": "analyze/v4"}',
    "build.log": "bst build all.bst\n",
    "element-slice.json": '["core.bst"]',
    "capture-context.txt": "captured for a guard\n",
}

# Written into the snapshot and expected *not* to travel: the layout
# calls both DERIVED, which means "absent means nothing; it is rebuilt
# on demand", so carrying them cannot make the far report quieter.
DERIVED_FILES = {
    "run/chrome_trace.json": "{}",
    ".size": "12345",
}


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
    """A capture with every non-DERIVED layout member present, plus the
    two DERIVED ones so their exclusion is observed rather than assumed.
    """
    path = os.path.join(run_store.runs_dir(project), STAMP)
    for relative, text in {**CAPTURE, **DERIVED_FILES}.items():
        _write(path, relative, text)
    return path


@pytest.fixture
def far(tmp_path_factory):
    root = str(tmp_path_factory.mktemp("far"))
    _write(root, "project.conf", "name: demo\n")
    return root


def _repack(source, destination, manifest=None, drop=(), extra=()):
    """Rewrite a bundle - the only way to forge one a newer `bga` wrote."""
    with tarfile.open(source, mode="r:gz") as original:
        entries = [(info, original.extractfile(info).read())
                   for info in original.getmembers()]
    if manifest is not None:
        payload = json.dumps(manifest).encode("utf-8")
        entries = [(info, payload) if info.name == bundle.MANIFEST_NAME
                   else (info, data) for info, data in entries]
        for info, _data in entries:
            if info.name == bundle.MANIFEST_NAME:
                info.size = len(payload)
    entries = [(info, data) for info, data in entries if info.name not in drop]
    with open(destination, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed, \
            tarfile.open(fileobj=compressed, mode="w") as archive:
            for info, data in entries:
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            for name, data in extra:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
    return destination


class TestTheBundleIsTheCaptureAndNotJustRun:

    def test_every_layout_member_that_exists_travels(self, snapshot, tmp_path):
        """The defect in one line: `run/` alone loses Plane 2.

        Derived from `CAPTURE_LAYOUT`, so the eighth member is covered
        by the contract naming it rather than by this list growing.
        """
        path, manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        packed = {member["path"] for member in manifest["members"]}
        expected = {relative for relative, presence, _contract
                    in bundle._layout_relative()
                    if presence != run_store.DERIVED and relative in CAPTURE}
        assert packed == expected
        beside_run = {p for p in packed if not p.startswith("run/")}
        assert "plane2.json" in beside_run and "host-samples.jsonl" in beside_run
        with tarfile.open(path) as archive:
            names = set(archive.getnames())
        assert names == {bundle.MANIFEST_NAME} | {
            bundle.MEMBER_PREFIX + p for p in expected}

    def test_derived_members_do_not_travel(self, snapshot, tmp_path):
        """`DERIVED` means absent costs nothing. `.size` would arrive
        stale and `chrome_trace.json` is rendered on demand."""
        _path, manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        packed = {member["path"] for member in manifest["members"]}
        assert packed.isdisjoint(DERIVED_FILES)

    def test_the_manifest_names_each_members_contract_version(
            self, snapshot, tmp_path):
        _path, manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        contracts = {member["path"]: member["contract"]
                     for member in manifest["members"]}
        assert contracts["run/graph.json"] == "graph/v9"
        assert contracts["plane2.json"] == "plane2/v3"
        assert contracts["host-samples.jsonl"] == "host-samples/v1"
        assert contracts["build.log"] is None, (
            "a member with no contract must say so rather than borrow one")
        assert manifest["schema"] == bundle.SCHEMA
        assert manifest["bga_version"]

    def test_a_fresh_capture_is_not_refused_by_its_own_bga(
            self, snapshot, tmp_path, far):
        """The regression this item measured while it was built.

        `readable_contracts()` was `contracts.ids() | superseded()`, and
        the first real bundle was refused for carrying `graph/v9`,
        `trace/v9` and `run-context/v9` — *input* shapes no `bga` module
        stamps, so in neither set. A round-trip that refuses itself is
        the whole feature failing closed.
        """
        path, _manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        target, _loaded = bundle.load(path, far)
        assert os.path.isfile(os.path.join(target, "run", "graph.json"))


class TestTheSwitchSaysWhatItLeftOut:

    def test_no_plane2_drops_the_plane2_members_and_records_it(
            self, snapshot, tmp_path):
        _path, manifest = bundle.export(
            snapshot, str(tmp_path / "b.tar.gz"), include_plane2=False)
        packed = {member["path"] for member in manifest["members"]}
        assert not any(bundle.is_plane2(p) for p in packed)
        assert set(manifest["excluded"]) == {
            "plane2.json", "plane2-resource.json"}
        assert "host-samples.jsonl" in packed, (
            "host sampling is not the Plane 2 capture and is small; "
            "dropping it would make the far report quieter for nothing")

    def test_everything_ships_by_default(self, snapshot, tmp_path):
        _path, manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        assert manifest["excluded"] == []
        assert "plane2.json" in {m["path"] for m in manifest["members"]}


class TestTheFarSideRefusesRatherThanHalfReads:

    def test_a_newer_bundle_format_is_refused_by_name(
            self, snapshot, tmp_path, far):
        path, manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        manifest["schema"] = "bundle-manifest/v2"
        manifest["bga_version"] = "9.9.9"
        forged = _repack(path, str(tmp_path / "newer.tar.gz"), manifest)
        with pytest.raises(bundle.BundleError) as error:
            bundle.load(forged, far)
        assert "bundle-manifest/v2" in str(error.value)
        assert "9.9.9" in str(error.value)
        assert run_store.list_snapshots(far) == []

    def test_a_member_contract_this_bga_cannot_read_is_refused(
            self, snapshot, tmp_path, far):
        path, manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        for member in manifest["members"]:
            if member["path"] == "run/graph.json":
                member["contract"] = "graph/v10"
        forged = _repack(path, str(tmp_path / "newer.tar.gz"), manifest)
        with pytest.raises(bundle.BundleError) as error:
            bundle.load(forged, far)
        assert "graph/v10" in str(error.value)
        assert run_store.list_snapshots(far) == [], (
            "a refusal that had already written half the members is the "
            "half-read this item exists to prevent")

    def test_a_declared_member_that_escapes_the_directory_is_refused(
            self, snapshot, tmp_path, far):
        """The traversal case, and it has to be *declared* to reach the
        clause under test.

        An undeclared escaping entry is caught by the manifest-membership
        check one line below, so a guard that only added one would pass
        with the traversal check deleted - measured exactly that way
        while this file was written.
        """
        path, manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        manifest["members"].append(
            {"path": "../../escaped.json", "presence": "conditional",
             "contract": None, "bytes": 2})
        forged = _repack(path, str(tmp_path / "escape.tar.gz"), manifest,
                         extra=[(bundle.MEMBER_PREFIX + "../../escaped.json",
                                 b"{}")])
        with pytest.raises(bundle.BundleError) as error:
            bundle.load(forged, far)
        assert "escapes the snapshot directory" in str(error.value)
        assert not os.path.exists(
            os.path.join(os.path.dirname(os.path.dirname(far)),
                         "escaped.json"))

    def test_an_entry_outside_the_member_prefix_is_refused_as_such(
            self, snapshot, tmp_path, far):
        """And the refusal names the prefix, so deleting that clause and
        falling through to the membership check reddens this."""
        path, _manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        forged = _repack(path, str(tmp_path / "loose.tar.gz"),
                         extra=[("escaped.json", b"{}")])
        with pytest.raises(bundle.BundleError) as error:
            bundle.load(forged, far)
        assert bundle.MEMBER_PREFIX in str(error.value)
        assert "is not a file under" in str(error.value)

    def test_a_directory_entry_under_the_prefix_is_refused(
            self, snapshot, tmp_path, far):
        """Only regular files are unpacked. A dir (or a symlink) entry
        is how an archive writes somewhere it did not declare."""
        path, _manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        with tarfile.open(path, mode="r:gz") as original:
            entries = [(info, original.extractfile(info).read())
                       for info in original.getmembers()]
        forged = str(tmp_path / "dir.tar.gz")
        with open(forged, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed, \
                tarfile.open(fileobj=compressed, mode="w") as archive:
                for info, data in entries:
                    archive.addfile(info, io.BytesIO(data))
                directory = tarfile.TarInfo(bundle.MEMBER_PREFIX + "sub")
                directory.type = tarfile.DIRTYPE
                archive.addfile(directory)
        with pytest.raises(bundle.BundleError) as error:
            bundle.load(forged, far)
        assert "is not a file under" in str(error.value)

    def test_a_manifest_naming_a_member_the_archive_lacks_is_refused(
            self, snapshot, tmp_path, far):
        path, _manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        forged = _repack(path, str(tmp_path / "short.tar.gz"),
                         drop=(bundle.MEMBER_PREFIX + "plane2.json",))
        with pytest.raises(bundle.BundleError) as error:
            bundle.load(forged, far)
        assert "plane2.json" in str(error.value)
        assert run_store.list_snapshots(far) == []

    def test_a_file_that_is_not_a_bundle_is_refused(self, tmp_path, far):
        plain = tmp_path / "notes.txt"
        plain.write_text("not an archive")
        with pytest.raises(bundle.BundleError):
            bundle.load(str(plain), far)


class TestTheStampIsTheCapturesIdentity:

    def test_the_stamp_is_preserved_rather_than_reassigned(
            self, snapshot, tmp_path, far):
        path, _manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        target, loaded = bundle.load(path, far)
        assert os.path.basename(target) == STAMP
        assert loaded["stamp"] == STAMP

    def test_the_same_bundle_loads_twice_without_complaint(
            self, snapshot, tmp_path, far):
        """Identical contents under one stamp is a re-send, not a
        collision - refusing it would make `scp` twice an error."""
        path, _manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        bundle.load(path, far)
        target, _again = bundle.load(path, far)
        assert os.path.basename(target) == STAMP

    def test_a_different_capture_under_the_same_stamp_is_refused(
            self, snapshot, tmp_path, far):
        path, _manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        bundle.load(path, far)
        _write(os.path.join(run_store.runs_dir(far), STAMP),
               "run/graph.json", '{"schema": "graph/v9", "changed": true}')
        with pytest.raises(bundle.BundleError) as error:
            bundle.load(path, far)
        assert "run/graph.json" in str(error.value)

    def test_the_host_manifest_arrives_byte_identical(
            self, snapshot, tmp_path, far):
        """`UX-186`'s cross-host refusal lives in `run-context.json`. A
        format that rewrote it would turn that refusal off by accident,
        which is the one way this row could do harm."""
        path, _manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        target, _loaded = bundle.load(path, far)
        near = os.path.join(snapshot, "run", "run-context.json")
        with open(near, "rb") as handle:
            original = handle.read()
        with open(os.path.join(target, "run", "run-context.json"), "rb") as h:
            assert h.read() == original


class TestTheCommandIsWired:

    def test_export_then_load_round_trips_through_the_cli(
            self, snapshot, project, tmp_path, far, monkeypatch, capsys):
        from bga.cli import main

        out = str(tmp_path / "carry.tar.gz")
        monkeypatch.chdir(project)
        assert main(["bundle", "--export", "@" + STAMP, "-o", out]) == 0
        assert "member(s)" in capsys.readouterr().out
        monkeypatch.chdir(far)
        assert main(["bundle", "--load", out]) == 0
        printed = capsys.readouterr().out
        assert STAMP in printed and "bga analyze @last" in printed

    def test_a_refused_bundle_exits_two_and_says_why(
            self, snapshot, project, tmp_path, far, monkeypatch, capsys):
        from bga.cli import main

        path, manifest = bundle.export(snapshot, str(tmp_path / "b.tar.gz"))
        manifest["schema"] = "bundle-manifest/v2"
        forged = _repack(path, str(tmp_path / "newer.tar.gz"), manifest)
        monkeypatch.chdir(far)
        assert main(["bundle", "--load", forged]) == 2
        assert "bundle-manifest/v2" in capsys.readouterr().err
