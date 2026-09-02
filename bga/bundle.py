"""UX-520: the whole capture in one file, and what the far side refuses.

`run/` is not the capture. `UX-381` made the layout a contract, and half
of what a reader needs sits *beside* `run/` — the Plane 2 report, the raw
trace, the host samples, the published analysis. A user who tars `run/`,
which is the directory every command's help names, carries Plane 1 and
leaves Plane 2 behind.

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
from typing import Dict, List, Optional, Tuple

from . import __version__, contracts, run_store

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


def _layout_relative() -> List[Tuple[str, str, Optional[str]]]:
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
            ) -> Tuple[List[dict], List[str]]:
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

    Three sources, and the third is not decoration. `contracts.ids()`
    inventories what `bga` *stamps* and `superseded()` what it still
    reads after retiring (`UX-297`) — but `graph/v9`, `trace/v9` and
    `run-context/v9` are *input* shapes that no `bga` module stamps, so
    they are in neither. Measured while `UX-520` was built: the first
    real bundle was refused for carrying all three. `CAPTURE_LAYOUT` is
    the contract that says what a capture holds, so it is the authority
    on what this build reads out of one. `UX-540` is the row for the
    registry gap itself.
    """
    from_layout = {contract for _relative, _presence, contract
                   in _layout_relative() if contract}
    return from_layout | set(contracts.ids()) | set(contracts.superseded())


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


def export(snapshot: str, output: Optional[str] = None,
           include_plane2: bool = True,
           now: Optional[datetime] = None) -> Tuple[str, dict]:
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
    with open(destination, "wb") as raw:
        # `mtime=0` so the same snapshot packs to the same bytes twice;
        # a bundle a user diffs against a re-export should be equal.
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
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
        raise BundleError(f"{bundle} is not a readable archive: {error}")
    except KeyError:
        raise BundleError(
            f"{bundle} has no {MANIFEST_NAME}, so it is not a bga bundle. "
            f"`bga bundle --export` writes one.")
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
            f"this bundle carries contract(s) this bga does not read: "
            f"{', '.join(unknown)}. It was packed by bga "
            f"{manifest.get('bga_version', 'unknown')}; upgrade to read it. "
            f"Nothing was written.")


def _safe_members(archive: tarfile.TarFile, manifest: dict
                  ) -> List[tarfile.TarInfo]:
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
            f"the manifest names {len(missing)} member(s) the archive does "
            f"not hold ({', '.join(missing[:4])}); refusing to half-load it")
    return [found[path] for path in sorted(found)]


def _differs(target: str, archive: tarfile.TarFile,
             infos: List[tarfile.TarInfo]) -> List[str]:
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


def load(bundle: str, project: str) -> Tuple[str, dict]:
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
                    f"{len(changed)} member(s) differ "
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


def describe(manifest: dict) -> Dict[str, int]:
    """The counts the two commands print, so both say the same thing."""
    return {
        "members": len(manifest.get("members", ())),
        "bytes": sum(member.get("bytes", 0)
                     for member in manifest.get("members", ())),
        "excluded": len(manifest.get("excluded", ())),
    }
