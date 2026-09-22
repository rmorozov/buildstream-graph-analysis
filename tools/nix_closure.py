#!/usr/bin/env python3
"""UX-927: a pin's whole closure, staged at its own absolute store paths.

`nix_store_fetch` stages one NAR per pin and answers its two absolute
references - interpreter and RUNPATH - with a symlink into the sysroot's
glibc. A compiler is not that: gcc's driver reaches separate gcc,
binutils, libc, header and support store paths, so a partial closure is
a sysroot that builds by reaching outside itself. This walks the
`.narinfo` `References` transitively and stages every path reached.

Nothing is relocated. Each path lands at `<dest>/nix/store/<hash>-name`,
its content-address intact, because the mechanism that keeps the host's
store out is a bind mount of `<dest>/nix/store` at `/nix/store` in the
sandbox, not a rewritten binary (UX-925 ruled patchelf out).

Measured 2026-09-22 on `ipr6y28...-gcc-14.3.0`: 15 paths, 298.6 MiB
unpacked, 92.9 MiB fetched, **every one `zstd`** - so `UX-915`'s
stdlib-`lzma` choice stages none of it. `zstd` is therefore declared
rather than assumed: `zstd_backend` probes the four that exist and the
staging fails by name when none does.

`dangling_store_refs` is the completeness assertion, and it runs on a
machine with no Nix at all: a staged tree naming a store path it does
not carry would have resolved that path on the staging host.
"""
import argparse
import hashlib
import os
import re
import sys
import urllib.request
from collections.abc import Iterable
from typing import Optional

from tools import nix_store_fetch

CACHE = "https://cache.nixos.org/"

STORE = "/nix/store"

#: A store path is `<32 nix-base32 chars>-<name>`; the hash alone is
#: what `cache.nixos.org` keys a `.narinfo` by.
STORE_REF = re.compile(rb"/nix/store/([0-9a-df-np-sv-z]{32})-([\w.+-]+)")

ALPHABET = "0123456789abcdfghijklmnpqrsvwxyz"


def nix32_decode(text: str) -> bytes:
    """Nix's own base32, least-significant digit first. Checked against
    both `nix_store_fetch.PINS` digests, which were typed as hex."""
    out = bytearray((len(text) * 5) // 8)
    for n, char in enumerate(reversed(text)):
        digit = ALPHABET.index(char)
        i, j = divmod(n * 5, 8)
        out[i] |= (digit << j) & 0xFF
        carry = digit >> (8 - j)
        if carry:
            out[i + 1] |= carry
    return bytes(out)


def digest_hex(field: str) -> str:
    """`sha256:<nix-base32>` (what a narinfo carries) as hex."""
    algo, _, value = field.partition(":")
    if algo != "sha256":
        raise ValueError(f"unsupported narinfo digest {field!r}")
    return value if len(value) == 64 else nix32_decode(value).hex()


def _zstd_backends():
    """Every decompressor for `zstd` this interpreter could have, in the
    order they are tried. Stdlib first (3.14 carries one), then the two
    wheels, then the CLI - so a host that already answers costs nothing."""
    def _stdlib(data):
        from compression import zstd
        return zstd.decompress(data)

    def _zstandard(data):
        import zstandard
        return zstandard.ZstdDecompressor().decompress(
            data, max_output_size=_MAX_NAR)

    def _pyzstd(data):
        import pyzstd
        return pyzstd.decompress(data)

    def _cli(data):
        import subprocess
        return subprocess.run(["zstd", "-dc"], input=data, check=True,
                              stdout=subprocess.PIPE).stdout

    return (("compression.zstd", _stdlib), ("zstandard", _zstandard),
            ("pyzstd", _pyzstd), ("zstd(1)", _cli))


#: `zstandard` needs an output bound up front and a gcc store path is
#: 230 MiB unpacked, so this is the largest NAR the stager will take -
#: a cap, not a measurement.
_MAX_NAR = 4 << 30


def _first_backend(data: bytes) -> Optional[tuple[str, bytes]]:
    """The first backend that reads `data`, as `(name, result)`, or
    `None`. One loop rather than two, so what `--check` reports is what
    a staging run would really use."""
    for name, call in _zstd_backends():
        try:
            return name, call(data)
        except Exception:  # any backend's own failure means "not this one"
            pass
    return None


#: The smallest valid zstd frame: magic, a header, an empty raw block.
_EMPTY_FRAME = b"\x28\xb5\x2f\xfd\x20\x00\x01\x00\x00"


def zstd_backend() -> Optional[str]:
    """The name of the backend that answers here, or `None`. Declared
    rather than assumed: `--check` prints it, so a staged tree says what
    read it - UX-914's rule, one layer down."""
    found = _first_backend(_EMPTY_FRAME)
    return found[0] if found else None


def _zstd(data: bytes) -> bytes:
    found = _first_backend(data)
    if found is None:
        raise SystemExit(
            "nix_closure: this closure is `zstd` and nothing here reads it - "
            "install one of " + ", ".join(n for n, _ in _zstd_backends())
            + " (`pip install -e \".[nix]\"` carries `zstandard`)")
    return found[1]


def _xz(data: bytes) -> bytes:
    import lzma
    return lzma.decompress(data)


#: One entry per `Compression:` value the stager accepts. An absent key
#: is a hard error naming the value, never a silent pass-through: a NAR
#: handed to the reader still compressed reads as a malformed NAR.
DECOMPRESSORS = {"xz": _xz, "zstd": _zstd, "none": lambda data: data}


def decompress(compression: str, data: bytes) -> bytes:
    if compression not in DECOMPRESSORS:
        raise SystemExit(
            f"nix_closure: unsupported NAR compression {compression!r} "
            f"(known: {', '.join(sorted(DECOMPRESSORS))})")
    return DECOMPRESSORS[compression](data)


def parse_narinfo(text: str) -> dict[str, str]:
    """A narinfo is `Key: value` lines; `References` is space separated."""
    fields = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            fields[key.strip()] = value.strip()
    return fields


def _read(url: str, timeout: int = 180) -> bytes:
    if not url.startswith(("https:", "file:")):
        raise ValueError(f"{url}: only https (the cache) and file (tests) are read")
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def narinfo(store_hash: str, cache_dir: str, base: str = CACHE) -> dict[str, str]:
    """One path's narinfo, cached on disk. Unverifiable by construction -
    it carries the digests rather than having one - so it is re-read
    whenever the cached copy does not name the hash asked for."""
    cached = os.path.join(cache_dir, store_hash + ".narinfo")
    if os.path.exists(cached):
        with open(cached, encoding="utf-8") as handle:
            fields = parse_narinfo(handle.read())
        if fields.get("StorePath", "").startswith(f"{STORE}/{store_hash}-"):
            return fields
    text = _read(base + store_hash + ".narinfo").decode("utf-8")
    fields = parse_narinfo(text)
    if not fields.get("StorePath", "").startswith(f"{STORE}/{store_hash}-"):
        raise SystemExit(
            f"nix_closure: {base}{store_hash}.narinfo names "
            f"{fields.get('StorePath')!r}, not {store_hash}")
    os.makedirs(cache_dir, exist_ok=True)
    with open(cached, "w", encoding="utf-8") as handle:
        handle.write(text)
    return fields


def store_hash(path_or_ref: str) -> str:
    """`/nix/store/<hash>-name`, or a bare `<hash>-name` reference."""
    return os.path.basename(path_or_ref).split("-", 1)[0]


def closure(roots: Iterable[str], cache_dir: str,
            base: str = CACHE) -> dict[str, dict[str, str]]:
    """Every store path the roots' `References` reach, transitively,
    keyed by hash. Sorted, so two runs stage in the same order and a
    diff of the manifest reads."""
    found: dict[str, dict[str, str]] = {}
    pending = sorted({store_hash(root) for root in roots})
    while pending:
        current = pending.pop()
        if current in found:
            continue
        fields = narinfo(current, cache_dir, base)
        found[current] = fields
        for ref in fields.get("References", "").split():
            if store_hash(ref) not in found:
                pending.append(store_hash(ref))
    return dict(sorted(found.items()))


def fetch_nar(fields: dict[str, str], cache_dir: str, base: str = CACHE) -> bytes:
    """The raw NAR behind one narinfo, gated on `NarHash`.

    `NarHash` is the store path's own content address; `FileHash`
    describes one *compression* of it, which a cache is free to replace.
    Measured 2026-09-22 from this container: `glibc-2.40-224` arrives as
    9,099,653 bytes against the narinfo's declared 9,096,823, with
    `FileHash` disagreeing and `NarHash` and `NarSize` both exact, while
    `gcc-14.3.0-lib` (also `zstd`) agrees on all three. So a `FileHash`
    mismatch warns and a `NarHash` mismatch is fatal - the other way
    round would refuse a correct store path over its wrapper."""
    nar_hash = digest_hex(fields["NarHash"])
    cached = os.path.join(cache_dir, nar_hash + ".nar")
    if os.path.exists(cached):
        with open(cached, "rb") as handle:
            raw = handle.read()
        if hashlib.sha256(raw).hexdigest() == nar_hash:
            return raw
    data = _read(base + fields["URL"])
    file_hash = digest_hex(fields["FileHash"])
    got = hashlib.sha256(data).hexdigest()
    if got != file_hash:
        print(f"nix_closure: {fields['URL']} sha256 {got}, narinfo FileHash "
              f"{file_hash} - recompressed; NarHash decides", file=sys.stderr)
    raw = decompress(fields.get("Compression", "none"), data)
    got = hashlib.sha256(raw).hexdigest()
    if got != nar_hash:
        raise SystemExit(
            f"nix_closure: {fields['StorePath']} unpacked to sha256 {got}, "
            f"narinfo NarHash {nar_hash}")
    if len(raw) != int(fields["NarSize"]):
        raise SystemExit(
            f"nix_closure: {fields['StorePath']} is {len(raw)} bytes, "
            f"narinfo NarSize {fields['NarSize']}")
    os.makedirs(cache_dir, exist_ok=True)
    with open(cached, "wb") as handle:
        handle.write(raw)
    return raw


def stage_closure(dest: str, roots: Iterable[str], cache_dir: str,
                  base: str = CACHE) -> list[dict[str, str]]:
    """Every path in the roots' closure, unpacked under `dest` at its own
    absolute store path. Returns the narinfos staged, in closure order."""
    staged = []
    for fields in closure(roots, cache_dir, base).values():
        target = dest + fields["StorePath"]
        if not os.path.isdir(target):
            nix_store_fetch.unpack_nar_data(
                fetch_nar(fields, cache_dir, base), target)
        staged.append(fields)
    return staged


def staged_hashes(dest: str) -> set:
    """The store paths really present under `dest`, read off the tree."""
    root = dest + STORE
    if not os.path.isdir(root):
        return set()
    return {name.split("-", 1)[0] for name in os.listdir(root)}


def missing_from(dest: str, paths: Iterable[str]) -> list[str]:
    """Closure members the staged tree does not carry."""
    present = staged_hashes(dest)
    return sorted(path for path in paths if store_hash(path) not in present)


def dangling_store_refs(dest: str) -> list[tuple[str, str]]:
    """Every `/nix/store/<hash>-name` a staged file names that `dest`
    does not carry, as `(file, reference)`. This is the whole of the
    isolation claim, and it needs no sandbox and no Nix: a path named
    but not staged is one the staging host answered."""
    present, dangling = staged_hashes(dest), []
    for base, _dirs, files in os.walk(dest + STORE):
        for name in files:
            path = os.path.join(base, name)
            if os.path.islink(path):
                continue
            with open(path, "rb") as handle:
                blob = handle.read()
            for digest, tail in {m.groups() for m in STORE_REF.finditer(blob)}:
                if digest.decode() not in present:
                    ref = f"{STORE}/{digest.decode()}-{tail.decode()}"
                    dangling.append((os.path.relpath(path, dest), ref))
    return sorted(set(dangling))


def default_cache_dir() -> str:
    return os.path.join(
        os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
        "bga", "nix-store")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("dest", help="the sysroot root to stage under")
    parser.add_argument("--root", action="append", dest="roots", default=[],
                        help="a store path or hash to close over (repeatable)")
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--base", default=CACHE)
    parser.add_argument("--check", action="store_true",
                        help="stage nothing; report the staged tree's gaps")
    parser.add_argument("--plan", action="store_true",
                        help="walk the narinfos and print the closure only")
    args = parser.parse_args(argv)
    cache_dir = args.cache_dir or default_cache_dir()

    if args.check:
        dangling = dangling_store_refs(args.dest)
        print(f"zstd backend\t{zstd_backend() or 'none'}")
        print(f"staged paths\t{len(staged_hashes(args.dest))}")
        for path, ref in dangling:
            print(f"dangling\t{path}\t{ref}")
        if dangling:
            print(f"nix_closure: {len(dangling)} reference(s) not staged - "
                  f"this tree resolves through the host's {STORE}",
                  file=sys.stderr)
            return 1
        return 0

    if not args.roots:
        parser.error("--root is required unless --check")
    if args.plan:
        found = closure(args.roots, cache_dir, args.base)
        total = sum(int(f["NarSize"]) for f in found.values())
        for fields in found.values():
            print(f"{fields.get('Compression', 'none')}\t"
                  f"{int(fields['NarSize'])}\t{fields['StorePath']}")
        print(f"#\t{len(found)} paths\t{total} bytes unpacked")
        return 0
    for fields in stage_closure(args.dest, args.roots, cache_dir, args.base):
        print(f"{fields.get('Compression', 'none')}\t{fields['StorePath']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
