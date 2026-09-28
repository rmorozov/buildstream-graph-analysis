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
import collections
import decimal
import functools
import gzip
import io
import json
import os
import re
import tarfile
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Optional

from . import __version__, anonymize, contracts, disclosure, public_names, run_store
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


def anonymized_manifest(manifest: dict, key: bytes, pmap: "anonymize.PseudonymMap",
                        junctions: tuple = ()) -> dict:
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
    if junctions:
        # UX-1065: which declared junctions passed their names through, and
        # how many - the export's own account, not a claim the far side must trust blind.
        transformed["public_junctions"] = list(junctions)
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


#: `anonymized-bundle.md` 6.2: the class F paths a grammar rebuilds; every other F is dropped.
_COMMAND_PATHS = frozenset({
    ("plane2/v3", "redundant_operations[].example_cmd"),
    ("plane2/v3", "redundant_operations[].signature"),
    ("plane2/v3", "stream_coverage.cpu_disagreements[].cmd"),
})

#: The class D paths holding a hostname; every other host fact is kept (section 8).
_HOSTNAME_PATHS = frozenset({("run-context/v9", "host")})

#: Every class H path: its clock and its microseconds per unit. An H path
#: missing here refuses, since a shift on the wrong clock breaks every delta.
_TIME_AXES = {
    ("trace/v9", "spans[].ts_us"): ("wall", 1),
    ("trace/v9", "phases[].ts_us"): ("wall", 1),
    ("run-context/v9", "wall_clock.start_us"): ("wall", 1),
    ("run-context/v9", "wall_clock.end_us"): ("wall", 1),
    ("run-context/v9", "queue_seam.requested_at_us"): ("wall", 1),
    ("run-context/v9", "queue_seam.started_at_us"): ("wall", 1),
    ("host-samples/v1", "wall_at_start"): ("wall", 10**6),
    ("host-samples/v1", "monotonic_at_start"): ("monotonic", 10**6),
    ("host-samples/v1", "t"): ("monotonic", 10**6),
}

#: 6.2: a dictionary token shorter than this is never scanned for.
RESIDUE_MIN = 4

#: Where each clock's earliest instant lands, in µs: the wall clock at
#: 2000-01-01T00:00:00Z, since the analyzer reads a 0 start as no start.
CANONICAL_ORIGIN_US = {"wall": 946684800 * 10**6, "monotonic": 0}


class _Recording(anonymize.PseudonymMap):
    """`pmap`, noting every original that reaches it: the residue scan's dictionary."""

    def __init__(self, pmap: "anonymize.PseudonymMap"):
        self.path, self.pmap, self.originals = pmap.path, pmap, set()

    def resolve(self, pseudonym: str):
        return self.pmap.resolve(pseudonym)

    def has(self, pseudonym: str) -> bool:
        return self.pmap.has(pseudonym)

    def save(self) -> None:
        self.pmap.save()

    def add(self, pseudonym: str, original: str) -> None:
        self.originals.add(original.split("\0", 1)[-1])
        self.pmap.add(pseudonym, original)


def _join(pattern: str, step: str) -> str:
    return f"{pattern}.{step}" if pattern else step


#: `rename` returns this to mean "drop the whole entry, key and value" -
#: a class-F/G map key carries nothing an export can keep as a key.
_DROP_ENTRY = object()


def _rewrite(node: dict, value, pattern: str, leaf, rename):
    """`value` rebuilt in place under the policy trie: key and list order kept."""
    if value is None:
        return None
    if isinstance(value, dict):
        placeholder = next((k for k in node if k.startswith("{")), None)
        out = {}
        for name, item in value.items():
            if name in node and not name.startswith(("{", "[", ".")):
                out[name] = _rewrite(node[name], item, _join(pattern, name), leaf, rename)
            elif placeholder is None:
                raise BundleError(f"{pattern}.{name}: not named by the policy")
            else:
                renamed = rename(placeholder[1:-1], name)
                if renamed is _DROP_ENTRY:
                    continue
                out[renamed] = _rewrite(
                    node[placeholder], item, _join(pattern, placeholder), leaf, rename)
        return out
    if isinstance(value, list):
        return [_rewrite(node["[]"], item, pattern + "[]", leaf, rename) for item in value]
    return leaf(node["."], pattern, value)


class _Anonymizer:
    """One export's walk: the values it rewrote, per class, and what it kept verbatim."""

    def __init__(self, key: bytes, pmap: "anonymize.PseudonymMap", public: frozenset = frozenset(),
                public_junctions: frozenset = frozenset()):
        self.key, self.pmap, self.public = key, _Recording(pmap), public
        self.public_junctions = public_junctions
        self.counts: collections.Counter = collections.Counter()
        self.kept: set = set()
        self.times: dict = collections.defaultdict(list)
        self.origins: dict = {}
        self.policy = ""

    def _axis(self, pattern: str) -> tuple[str, int]:
        axis = _TIME_AXES.get((self.policy, pattern))
        if axis is None:
            raise BundleError(f"{self.policy} {pattern}: a time with no declared clock")
        return axis

    def _instant(self, pattern: str, value) -> decimal.Decimal:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise BundleError(f"{self.policy} {pattern}: a time that is not a number")
        return decimal.Decimal(repr(value))

    def collect(self, policy: str, trie: dict, document) -> None:
        """The first pass: every instant on each clock, so one origin shifts them all."""
        def leaf(klass, pattern, value):
            if klass == "H":
                clock, per_unit = self._axis(pattern)
                self.times[clock].append(self._instant(pattern, value) * per_unit)
            return value
        self.policy = policy
        _rewrite(trie, document, "", leaf, lambda _klass, name: name)

    def rewrite(self, policy: str, trie: dict, document):
        if not self.origins:
            self.origins = {clock: min(t).to_integral_value(decimal.ROUND_FLOOR)
                            - CANONICAL_ORIGIN_US.get(clock, 0)
                            for clock, t in self.times.items()}
        self.policy = policy
        return _rewrite(trie, document, "", self._leaf, self._rename)

    def _rename(self, klass: str, name: str):
        """A map key's own class. `_leaf` returns `None` only for a
        class-F/G value - dropped, not stringified into the literal key
        `"None"` - so `_rewrite` drops the whole entry on that sentinel."""
        if klass == "C":
            return name
        renamed = self._leaf(klass, "", name)
        return _DROP_ENTRY if renamed is None else str(renamed)

    def _leaf(self, klass: str, pattern: str, value):
        head, key, pmap = klass[0], self.key, self.pmap
        if head == "B":
            return self._public(klass[2:], value)
        hostname = head == "D" and (self.policy, pattern) in _HOSTNAME_PATHS
        if head == "C" or (head == "D" and not hostname) or (
                head == "A" and not isinstance(value, str)):
            if isinstance(value, str):
                self.kept.add(value)
            return value
        if head == "A":
            return self._element_name(value, key, pmap)
        command = head == "F" and (self.policy, pattern) in _COMMAND_PATHS
        self.counts[{"F": "F rebuilt" if command else "F dropped"}.get(head, head)] += 1
        if hostname:
            pmap.originals.add(str(value))
            return anonymize.pseudonymize(str(value), "host", key, pmap)
        if head == "E":
            return anonymize.rekey_hash(value, key, pmap)
        if command:
            return self._command(value)
        if head in "FG":
            return None
        clock, per_unit = self._axis(pattern)
        shifted = self._instant(pattern, value) - self.origins[clock] / per_unit
        if isinstance(value, int) and shifted == shifted.to_integral_value():
            return int(shifted)
        return float(shifted)

    def _element_name(self, value: str, key: bytes, pmap):
        """A class-A `.bst` name: whole, junction-only, or fully pseudonymized.

        UX-1065: a declared junction's own name is never the secret; a
        listed member's name is public too, so both pass through - only the
        rest of the path, and an unlisted element under a declared junction,
        still reach `pseudonymize_identifier`.
        """
        if value in self.public:
            self.kept.add(value)
            return value
        junction, sep, rest = value.partition(":")
        if sep and junction in self.public_junctions and rest.endswith(".bst"):
            self.counts["A"] += 1
            self.kept.add(junction)
            pmap.originals.add(rest)
            return f"{junction}{sep}{anonymize.pseudonymize_element_path(rest, key, pmap)}"
        self.counts["A"] += 1
        pmap.originals.add(value)
        return anonymize.pseudonymize_identifier(value, key, pmap)

    def _command(self, value):
        """Rebuilt through the bare map: an argument is not a known name, so
        it joins no dictionary; the words kept verbatim join the review."""
        rebuilt = anonymize.rebuild_command(
            value, self.key, self.pmap.pmap, disclosure.VOCABULARIES["binary"].allowed)
        if isinstance(value, str) and isinstance(rebuilt, str):
            words = {w.split("=")[0] for w in value.split()}
            self.kept.update(w.split("=")[0] for w in rebuilt.split() if w.split("=")[0] in words)
        return rebuilt

    def _public(self, vocabulary: str, value):
        vocab = disclosure.VOCABULARIES[vocabulary]
        if vocab.admits(value):
            self.kept.add(value)
            return value
        if vocab.fallback is None or not isinstance(value, str):
            raise BundleError(f"{self.policy}: a {vocabulary} value off its allowlist, no fallback")
        self.counts["B"] += 1
        if vocabulary == "toolchain":
            return anonymize.pseudonymize_toolchain(value, self.key, self.pmap)
        cls = next(c for c, p in anonymize.CLASS_PREFIXES.items() if p == vocab.fallback)
        return anonymize.pseudonymize(value, cls, self.key, self.pmap)


def _read_documents(source: str) -> list:
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    try:
        if source.endswith(".jsonl"):
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        return [json.loads(text)]
    except ValueError as error:
        raise BundleError(f"{os.path.basename(source)} is not JSON ({error}); refusing it") from None


def _write_documents(documents: list) -> bytes:
    lines = [json.dumps(d, ensure_ascii=False) for d in documents]
    return ("\n".join(lines) + "\n").encode("utf-8")


@functools.cache
def _public_words() -> frozenset:
    """Schema keys, vocabulary and layout names: a legitimate bundle holds
    them, so a name equal to one is scanned only as its whole value."""
    phrases = {SCHEMA, MANIFEST_NAME, MEMBER_PREFIX, "key_fingerprint", "bga_version",
               "stamp", "members", "excluded", "presence", "contract", "bytes", "path"}
    for policy in disclosure.POLICIES.values():
        phrases.update(pattern.replace("[]", "") for pattern in policy)
        phrases.update(step for pattern in policy for step in pattern.replace("[]", "").split("."))
    for vocab in disclosure.VOCABULARIES.values():
        if isinstance(vocab.allowed, frozenset):
            phrases.update(vocab.allowed)
    phrases.update(disclosure.TREATMENTS)
    for _path, presence, contract, _what in run_store.CAPTURE_LAYOUT:
        phrases.update(filter(None, (presence, contract)))
    words = set()
    for phrase in phrases:
        words.add(phrase.lower())
        words.update(w for w in re.split(r"[^a-z0-9]+", phrase.lower()) if w)
    return frozenset(words)


def residue_dictionary(originals) -> set:
    """6.2: every original of `RESIDUE_MIN` or more characters, less the public words."""
    public = _public_words()
    return {o for o in originals if isinstance(o, str) and len(o) >= RESIDUE_MIN
            and not o.isdigit() and o.lower() not in public}


def _residue_pattern(dictionary) -> tuple[Optional[re.Pattern], dict]:
    variants, public = {}, _public_words()
    for token in dictionary:
        low = token.lower()
        for form in {low, re.sub(r"[-_.]", "", low),
                     *(re.sub(r"[-_.]", sep, low) for sep in "-_.")}:
            if form == low or (len(form) >= RESIDUE_MIN and form not in public):
                variants.setdefault(form, token)
    if not variants:
        return None, variants
    alternation = "|".join(map(re.escape, sorted(variants, key=len, reverse=True)))
    return re.compile(rf"(?<![a-z0-9])(?:{alternation})(?![a-z0-9])"), variants


def residue(archive: bytes, dictionary) -> list[str]:
    """6.2's tripwire over the decoded archive, headers and manifest included:
    `member: token` for every dictionary token still found in it."""
    pattern, variants = _residue_pattern(dictionary)
    hits: list[str] = []
    if pattern is None:
        return hits
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for info in tar.getmembers():
            fields = [info.name, info.uname, info.gname, info.linkname,
                      *map(str, info.pax_headers.values())]
            handle = tar.extractfile(info)
            if handle is not None:
                fields.append(handle.read().decode("utf-8", "replace"))
            found = {variants[m] for m in pattern.findall("\n".join(fields).lower())}
            hits.extend(f"{info.name}: {token}" for token in sorted(found))
    return hits


def _pack(manifest: dict, payloads: dict) -> bytes:
    raw = io.BytesIO()
    body = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed, \
            tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        archive.addfile(neutral_tarinfo(MANIFEST_NAME, len(body)), io.BytesIO(body))
        for relative, payload in payloads.items():
            archive.addfile(neutral_tarinfo(MEMBER_PREFIX + relative, len(payload)),
                            io.BytesIO(payload))
    return raw.getvalue()


def review_screen(destination: str, manifest: dict, dropped: list,
                  walk: _Anonymizer, dictionary: set) -> str:
    """6.8's one screen: what was substituted, what travels verbatim, what was dropped."""
    counts = " · ".join(f"{k} {v}" for k, v in sorted(walk.counts.items())) or "none"
    kept = sorted(walk.kept)
    return "\n".join([
        f"Anonymized bundle {destination}: {plural(len(manifest['members']), 'member')}",
        f"  members: {', '.join(m['path'] for m in manifest['members'])}",
        f"  dropped: {', '.join(dropped) or 'none'}",
        f"  values rewritten, per class: {counts}",
        f"  kept verbatim ({len(kept)}): {', '.join(kept) or 'none'}",
        f"  residue scan: clean over {plural(len(dictionary), 'dictionary token')}; "
        f"a tripwire, blind to a name it never held",
        "  the graph's shape alone can identify a project (anonymized-bundle.md 6.5)",
        f"  key fingerprint {manifest['key_fingerprint']}; the map stays on this machine",
    ])


def _untreated() -> list[str]:
    return [relative for relative, _presence, _contract in _layout_relative()
            if relative not in disclosure.TREATMENTS]


def _anonymized_members(snapshot: str, packed: list, walk: _Anonymizer
                        ) -> tuple[list, dict, list]:
    """Every packed member by its treatment: `(shipped, payloads, dropped)`;
    refuses the whole export on one disclosure gap."""
    shipped, payloads, dropped, documents, refused = [], {}, [], {}, []
    for member in packed:
        relative, source = member["path"], os.path.join(snapshot, member["path"])
        treatment = disclosure.TREATMENTS[relative]
        if treatment == disclosure.DROP:
            dropped.append(relative)
            continue
        shipped.append(dict(member))
        if treatment == disclosure.KEEP:
            with open(source, "rb") as handle:
                payloads[relative] = handle.read()
            continue
        documents[relative] = _read_documents(source)
        refused.extend(f"{relative}: {gap}" for gap in disclosure.gaps(
            relative, member["contract"], documents[relative]))
    if refused:
        raise BundleError(
            f"{plural(len(refused), 'value path')} the disclosure policy does not "
            f"clear, so nothing was written:\n  " + "\n  ".join(refused))
    payloads.update(_transformed(shipped, documents, walk))
    for member in shipped:
        member["bytes"] = len(payloads[member["path"]])
    return shipped, {m["path"]: payloads[m["path"]] for m in shipped}, dropped


def _transformed(shipped: list, documents: dict, walk: _Anonymizer) -> dict:
    """Two passes: every instant first, so one origin per clock shifts them all."""
    tries = {}
    for member in shipped:
        if member["path"] in documents:
            policy = disclosure.policy_key(member["path"], member["contract"])
            tries[member["path"]] = policy, disclosure.compile_policy(disclosure.POLICIES[policy])
    for relative, (policy, trie) in tries.items():
        for document in documents[relative]:
            walk.collect(policy, trie, document)
    return {relative: _write_documents([walk.rewrite(policy, trie, document)
                                        for document in documents[relative]])
            for relative, (policy, trie) in tries.items()}


def export_anonymized(snapshot: str, key: bytes, pmap: "anonymize.PseudonymMap",
                      output: Optional[str] = None,
                      *, approve: Callable[[str], bool]) -> tuple[str, dict]:
    """Every member walked by its `disclosure` treatment and policy, packed
    with neutral metadata (6.9), residue-scanned decoded, then shown to
    `approve`; nothing is written, map included, unless it returns true.

    Unreleased: no command reaches this until `UX-1063`'s guard is green.
    """
    if not os.path.isdir(snapshot):
        raise BundleError(f"{snapshot} is not a snapshot directory")
    untreated = _untreated()
    if untreated:
        raise BundleError(f"{plural(len(untreated), 'capture-layout row')} with no "
                          f"anonymized treatment: {', '.join(untreated)}; nothing was written")
    manifest = manifest_for(snapshot)
    if not manifest["members"]:
        raise BundleError(
            f"{snapshot} holds none of the files the capture-layout "
            f"contract names, so there is nothing to carry")
    # UX-1065: the project the snapshot sits under (`<project>/.bga/runs/<stamp>`),
    # so a declared public junction's config is read without a second argument.
    project = os.path.dirname(os.path.dirname(os.path.dirname(snapshot)))
    declared = run_store.public_junctions(project)
    try:
        public, junctions = public_names.public_names(declared) if declared else (frozenset(), [])
    except public_names.PublicNamesError as error:
        raise BundleError(str(error)) from error
    walk = _Anonymizer(key, pmap, public, frozenset(declared))
    shipped, payloads, dropped = _anonymized_members(snapshot, manifest["members"], walk)
    anon_manifest = anonymized_manifest(dict(manifest, members=shipped), key, walk.pmap, tuple(junctions))
    destination = output or anonymized_output()
    archive = _pack(anon_manifest, payloads)
    dictionary = residue_dictionary(walk.pmap.originals)
    hits = residue(archive, dictionary)
    if hits:
        raise BundleError("the residue scan found original names in the decoded "
                          "archive, so nothing was written:\n  " + "\n  ".join(hits))
    if not approve(review_screen(destination, anon_manifest, dropped, walk, dictionary)):
        raise BundleError("the owner did not approve the review; nothing was written")
    with open(destination, "wb") as handle:
        handle.write(archive)
    os.makedirs(os.path.dirname(pmap.path) or ".", exist_ok=True)
    pmap.save()
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
