"""UX-520: the whole capture in one file, and what the far side refuses.

`run/` is not the capture. `UX-381` made the layout a contract, and half of what a reader
needs sits *beside* `run/` — the Plane 2 report, the raw trace, the host samples, the
published analysis. A user who tars `run/`, which is the directory every command's help
names, carries Plane 1 and leaves Plane 2 behind.

So the member list is **derived from `CAPTURE_LAYOUT`**, never restated
here: a member added to the contract is bundled by existing. `DERIVED`
rows are skipped because that presence word already means "absent means
nothing; it is rebuilt on demand" — skipping one cannot make the far
machine's report quieter, which is the only reason the switch below is a
switch and not a heuristic.

And each member carries its contract version, so a bundle packed by a
newer `bga` is something this one recognises and *refuses* rather than
half-reads. That version is read from `CAPTURE_LAYOUT` — the contract
that says what each path holds — and not parsed out of the document,
because `UX-296` forbids opening the big Plane 2 file for one key. See
`readable_contracts` for what the far side checks it against.

The host manifest travels inside `run-context.json` untouched, so
`UX-186`'s cross-host refusal arrives on the far machine intact. A format
that rewrote it would turn that refusal off by accident.
"""
import gzip
import io
import json
import os
import tarfile
from datetime import datetime, timezone
from typing import Optional

from . import __version__, anonymize, contracts, run_store
from .plural import plural

SCHEMA = "bundle-manifest/v1"

#: The manifest, first member of the archive so a reader can refuse
#: before streaming the gigabyte behind it.
MANIFEST_NAME = "bundle.json"

#: Everything else lives under one prefix, so the archive can never
#: unpack over a sibling of the directory it was asked to fill.
MEMBER_PREFIX = "capture/"

_STAMP_TOKEN = "<stamp>"


class BundleError(Exception):
    """The bundle is not one this `bga` can read, or the store already
    holds a different capture under its stamp."""


def _layout_relative() -> list[tuple[str, str, Optional[str]]]:
    """`(snapshot-relative path, presence, contract)` for every file the
    capture-layout contract names inside one snapshot.

    Derived from `run_store.CAPTURE_LAYOUT` so the bundle cannot fall
    behind the directory it packs.
    """
    prefix = (f"{run_store.STORE_DIRNAME}/{run_store.RUNS_DIRNAME}/"
              f"{_STAMP_TOKEN}/")
    rows = []
    for path, presence, contract, _what in run_store.CAPTURE_LAYOUT:
        if not path.startswith(prefix) or path.endswith("/"):
            continue
        rows.append((path[len(prefix):], presence, contract))
    return rows


def is_plane2(relative: str) -> bool:
    """The Plane 2 capture, by the name the layout gives it.

    Derived rather than listed: the three `plane2*` members are the
    report, the raw trace it was folded from, and the two capacity
    scalars beside it, and a fourth would join them by being named.
    """
    return os.path.basename(relative).startswith("plane2")


def members(snapshot: str, include_plane2: bool = True
            ) -> tuple[list[dict], list[str]]:
    """What this snapshot would ship, and what the switch left out.

    `DERIVED` rows never ship (see the module docstring). A `REQUIRED`
    row that is absent is not an error here — `UX-156`'s failed build
    leaves a snapshot with no `run/`, and refusing to carry it would
    strand the half that survived.
    """
    packed, excluded = [], []
    for relative, presence, contract in _layout_relative():
        if presence == run_store.DERIVED:
            continue
        source = os.path.join(snapshot, relative)
        if not os.path.isfile(source):
            continue
        if not include_plane2 and is_plane2(relative):
            excluded.append(relative)
            continue
        packed.append({
            "path": relative,
            "presence": presence,
            "contract": contract,
            "bytes": os.path.getsize(source),
        })
    return packed, excluded


def readable_contracts() -> set:
    """Every contract id this `bga` can read out of a capture directory.

    Three kinds and one registry: what `bga` stamps, what it still reads
    after retiring (`UX-297`), and the input shapes nothing here stamps
    (`UX-540`). The third used to be a `CAPTURE_LAYOUT` union, because
    the registry did not know `graph/v9`, `trace/v9` or `run-context/v9`
    and the first real bundle was refused for carrying all three.
    """
    return (set(contracts.ids()) | set(contracts.superseded())
            | set(contracts.reads()))


def manifest_for(snapshot: str, include_plane2: bool = True,
                 now: Optional[datetime] = None) -> dict:
    packed, excluded = members(snapshot, include_plane2)
    return {
        "schema": SCHEMA,
        "bga_version": __version__,
        "stamp": os.path.basename(os.path.normpath(snapshot)),
        "packed_at": (now or datetime.now(timezone.utc)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "members": packed,
        "excluded": excluded,
    }


def default_output(stamp: str) -> str:
    return f"{stamp}.bga-bundle.tar.gz"


#: `anonymized-bundle.md` 6.9: a mode every reader sees the same way,
#: regardless of what the source file's own permissions happened to be.
_NEUTRAL_MODE = 0o644


def neutral_tarinfo(arcname: str, size: int) -> tarfile.TarInfo:
    """A `TarInfo` carrying no fact about the machine that made it.

    `tarfile.add()` copies the source's mtime, uid, gid, uname and gname
    into the header (`anonymized-bundle.md` 6.9); this builds one from
    scratch instead, so the only fields that vary are name and size.
    """
    info = tarfile.TarInfo(arcname)
    info.size = size
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mode = _NEUTRAL_MODE
    return info


def anonymized_manifest(manifest: dict, key: bytes, pmap: "anonymize.PseudonymMap"
                        ) -> dict:
    """`manifest`, with the fields 6.9 names as identifying dropped or
    pseudonymized: `stamp` through `anonymize.pseudonymize` (the stamp is
    a directory name, `.bga/runs/<stamp>/`), `packed_at` removed outright
    since a wall-clock time is not reconstructable from anything else in
    the bundle. The key never travels; only its fingerprint does, so a
    receiver can tell two anonymized bundles were keyed alike without
    holding the secret.
    """
    transformed = dict(manifest)
    transformed["stamp"] = anonymize.pseudonymize(
        manifest["stamp"], "directory", key, pmap)
    transformed.pop("packed_at", None)
    transformed["key_fingerprint"] = anonymize.key_fingerprint(key)
    return transformed


def anonymized_output() -> str:
    """The anonymized bundle's file name, which never carries the stamp
    (6.9): unlike `default_output`, nothing here varies by capture.
    """
    return "bga-bundle.tar.gz"


def export(snapshot: str, output: Optional[str] = None,
           include_plane2: bool = True,
           now: Optional[datetime] = None) -> tuple[str, dict]:
    """Write one archive holding this snapshot's capture-layout members.

    Returns the path written and the manifest inside it.
    """
    if not os.path.isdir(snapshot):
        raise BundleError(f"{snapshot} is not a snapshot directory")
    manifest = manifest_for(snapshot, include_plane2, now)
    if not manifest["members"]:
        raise BundleError(
            f"{snapshot} holds none of the files the capture-layout "
            f"contract names, so there is nothing to carry")
    destination = output or default_output(manifest["stamp"])

    payload = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    # `mtime=0` so the same snapshot packs to the same bytes twice;
    # a bundle a user diffs against a re-export should be equal.
    with open(destination, "wb") as raw, \
            gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed, \
            tarfile.open(fileobj=compressed, mode="w") as archive:
        info = tarfile.TarInfo(MANIFEST_NAME)
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
        for member in manifest["members"]:
            archive.add(
                os.path.join(snapshot, member["path"]),
                arcname=MEMBER_PREFIX + member["path"],
                recursive=False,
            )
    return destination, manifest


def export_anonymized(snapshot: str, key: bytes, pmap: "anonymize.PseudonymMap",
                      output: Optional[str] = None,
                      include_plane2: bool = True) -> tuple[str, dict]:
    """`export()`, but with no member's header or the manifest carrying a
    fact about this machine or this capture's identity (6.9).

    No `now`: `packed_at` is dropped from the manifest here (6.9), so the
    wall-clock time `manifest_for` would stamp it with never surfaces.

    Member *contents* are untouched here — walking them for names is
    `UX-1062`'s job; this is the metadata `UX-1062` builds on, so every
    header it writes and every manifest field it fills already carries
    nothing to scrub twice.
    """
    if not os.path.isdir(snapshot):
        raise BundleError(f"{snapshot} is not a snapshot directory")
    manifest = manifest_for(snapshot, include_plane2)
    if not manifest["members"]:
        raise BundleError(
            f"{snapshot} holds none of the files the capture-layout "
            f"contract names, so there is nothing to carry")
    anon_manifest = anonymized_manifest(manifest, key, pmap)
    destination = output or anonymized_output()

    payload = json.dumps(anon_manifest, indent=2, sort_keys=True).encode("utf-8")
    with open(destination, "wb") as raw, \
            gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed, \
            tarfile.open(fileobj=compressed, mode="w") as archive:
        payload_info = neutral_tarinfo(MANIFEST_NAME, len(payload))
        archive.addfile(payload_info, io.BytesIO(payload))
        for member in manifest["members"]:
            source = os.path.join(snapshot, member["path"])
            info = neutral_tarinfo(MEMBER_PREFIX + member["path"],
                                    os.path.getsize(source))
            with open(source, "rb") as handle:
                archive.addfile(info, handle)
    return destination, anon_manifest


def read_manifest(bundle: str) -> dict:
    """The manifest, or a refusal that says which of the two it is."""
    try:
        with tarfile.open(bundle, mode="r:gz") as archive:
            handle = archive.extractfile(MANIFEST_NAME)
            if handle is None:
                raise BundleError(
                    f"{bundle} has no {MANIFEST_NAME}, so it is not a bga "
                    f"bundle. `bga bundle --export` writes one.")
            manifest = json.loads(handle.read().decode("utf-8"))
    except tarfile.TarError as error:
        raise BundleError(f"{bundle} is not a readable archive: {error}") from error
    except KeyError:
        raise BundleError(
            f"{bundle} has no {MANIFEST_NAME}, so it is not a bga bundle. "
            f"`bga bundle --export` writes one.") from None
    if not isinstance(manifest, dict):
        raise BundleError(f"{bundle}'s {MANIFEST_NAME} is not an object")
    return manifest


def check_readable(manifest: dict) -> None:
    """Refuse a bundle this `bga` cannot read in full.

    Two separate refusals, because the remedies differ: a manifest
    schema this build does not know means the *bundle format* moved, and
    an unknown member contract means one document inside it did.
    """
    schema = manifest.get("schema")
    if schema != SCHEMA:
        raise BundleError(
            f"this bundle is {schema!r} and this bga reads {SCHEMA!r}. It was "
            f"packed by bga {manifest.get('bga_version', 'unknown')}; upgrade "
            f"to read it.")
    readable = readable_contracts()
    unknown = sorted({
        member.get("contract") for member in manifest.get("members", ())
        if member.get("contract") and member.get("contract") not in readable
    })
    if unknown:
        raise BundleError(
            f"this bundle carries {plural(len(unknown), 'contract')} this bga does not read: "
            f"{', '.join(unknown)}. It was packed by bga "
            f"{manifest.get('bga_version', 'unknown')}; upgrade to read it. "
            f"Nothing was written.")


def _safe_members(archive: tarfile.TarFile, manifest: dict
                  ) -> list[tarfile.TarInfo]:
    """The archive's own entries for the manifest's members.

    Read back from the archive rather than trusted from the manifest: a
    path is only unpacked if it is a regular file directly under
    `MEMBER_PREFIX` and the manifest declared it.
    """
    declared = {member["path"] for member in manifest.get("members", ())}
    found = {}
    for info in archive.getmembers():
        if info.name == MANIFEST_NAME:
            continue
        if not info.isfile() or not info.name.startswith(MEMBER_PREFIX):
            raise BundleError(
                f"{info.name} is not a file under {MEMBER_PREFIX}; refusing "
                f"to unpack this bundle")
        relative = info.name[len(MEMBER_PREFIX):]
        if os.path.isabs(relative) or ".." in relative.split("/"):
            raise BundleError(f"{info.name} escapes the snapshot directory")
        if relative not in declared:
            raise BundleError(
                f"{relative} is in the archive and not in its manifest; "
                f"refusing to unpack a bundle that does not describe itself")
        found[relative] = info
    missing = sorted(declared - set(found))
    if missing:
        raise BundleError(
            f"the manifest names {plural(len(missing), 'member')} the archive does "
            f"not hold ({', '.join(missing[:4])}); refusing to half-load it")
    return [found[path] for path in sorted(found)]


def _differs(target: str, archive: tarfile.TarFile,
             infos: list[tarfile.TarInfo]) -> list[str]:
    """The members already on disk under this stamp whose bytes differ."""
    changed = []
    for info in infos:
        relative = info.name[len(MEMBER_PREFIX):]
        existing = os.path.join(target, relative)
        if not os.path.isfile(existing):
            changed.append(relative)
            continue
        if os.path.getsize(existing) != info.size:
            changed.append(relative)
            continue
        handle = archive.extractfile(info)
        with open(existing, "rb") as current:
            if handle is None or current.read() != handle.read():
                changed.append(relative)
    return changed


def load(bundle: str, project: str) -> tuple[str, dict]:
    """Unpack into this project's store under the bundle's own stamp.

    The stamp is the capture's identity, so it is preserved rather than
    reassigned — a run carried to a laptop keeps the name it was
    compared under at home.
    """
    manifest = read_manifest(bundle)
    check_readable(manifest)
    stamp = manifest.get("stamp")
    if not stamp or os.path.isabs(stamp) or "/" in stamp or ".." in stamp:
        raise BundleError(f"the bundle's stamp is not a directory name: {stamp!r}")

    target = os.path.join(run_store.runs_dir(project), stamp)
    with tarfile.open(bundle, mode="r:gz") as archive:
        infos = _safe_members(archive, manifest)
        if os.path.exists(target):
            changed = _differs(target, archive, infos)
            if changed:
                raise BundleError(
                    f"{project} already holds snapshot {stamp} and "
                    f"{plural(len(changed), 'member')} differ "
                    f"({', '.join(changed[:4])}). Two different captures "
                    f"cannot share one identity; move or delete the existing "
                    f"one. Nothing was written.")
        os.makedirs(run_store.runs_dir(project), exist_ok=True)
        run_store.ensure_store_ignored(project)
        for info in infos:
            relative = info.name[len(MEMBER_PREFIX):]
            destination = os.path.join(target, relative)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            handle = archive.extractfile(info)
            with open(destination, "wb") as out:
                out.write(handle.read())
    return target, manifest


def describe(manifest: dict) -> dict[str, int]:
    """The counts the two commands print, so both say the same thing."""
    return {
        "members": len(manifest.get("members", ())),
        "bytes": sum(member.get("bytes", 0)
                     for member in manifest.get("members", ())),
        "excluded": len(manifest.get("excluded", ())),
    }
