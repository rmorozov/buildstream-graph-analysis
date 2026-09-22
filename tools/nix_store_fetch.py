#!/usr/bin/env python3
"""UX-915: a pinned GNU Make, fetched from `cache.nixos.org` without Nix.

Every Nix store path is served as one content-addressed `.nar.xz`, so a
pin here is (url, sha256 of the compressed file, store path, version)
and a fetch verifies before it unpacks - no Nix, no daemon, no root.
The alternative was building make from source: `ftp.gnu.org` is refused
at CONNECT from the dev container (measured 2026-09-21), and the GitHub
mirror route needs a gnulib bootstrap this host has no `autopoint` for.

Why pinned at all: `stage_cpp_toolchain.sh` copied the staging host's
own `/usr/bin/make`, so the version deciding every example's jobserver
auth style (`style_for_make_version`, UX-874) was whatever the host
installed - 4.3 on Ubuntu 24.04, below UX-841's 4.4 cutoff.

A staged binary carries a Nix ELF interpreter and RUNPATH, both
absolute; `stage_interpreter_link` answers both with one symlink to the
sysroot's already-staged glibc rather than a second glibc closure.
Measured safe: `objdump -T` on both pins stops at GLIBC_2.38, and
Ubuntu 24.04 (this repo's CI runner and dev container) carries 2.39.

The NAR format is the whole of `unpack_nar`: 8-byte little-endian
length, bytes, padded to 8 - regular (optionally executable), symlink,
directory.
"""
import argparse
import hashlib
import lzma
import os
import platform
import struct
import sys
import urllib.request
from typing import Optional

#: Store paths pinned per `platform.machine()`. `loader` is the glibc
#: dynamic linker whose staged copy locates the sysroot's own lib dir,
#: and `interpreter_dir` the absolute `lib/` the pinned binaries name.
PINS = {
    "x86_64": {
        "loader": "ld-linux-x86-64.so.2",
        "interpreter_dir": (
            "/nix/store/7nbi22pcc92y2fqbkyp7h3srvvklmckb-glibc-2.40-224/lib"),
        "paths": {
            "make-4.4": {
                "version": "GNU Make 4.4.1",
                "store_path": (
                    "/nix/store/fnvsac4yaw2146ig4p54xnnm6b6alkjw-gnumake-4.4.1"),
                "url": ("https://cache.nixos.org/nar/07k5xiavdyhv9v0qp7r5zjca5"
                        "1sfp0r7779ikhvcrwrafr5wm3qf.nar.xz"),
                "sha256": ("0e8fca4b762af3cc369c319d7332b84e"
                           "87a298fc259f8bc14e1bfab655ec651e"),
            },
            # UX-916: the other side of `style_for_make_version`. Same
            # channel, same glibc reference, so it costs one more nar.
            "make-4.2": {
                "version": "GNU Make 4.2.1",
                "store_path": (
                    "/nix/store/4320g8b6bl4wpgbmk0mdjr3rr2jr4xh6-gnumake-4.2.1"),
                "url": ("https://cache.nixos.org/nar/095yb6353v0ww7pjjyqwvaiqj"
                        "8i36qabanbhvk3dwm64gxvym5x3.nar.xz"),
                "sha256": ("a397ea777fc454dec6dc7059b5143623"
                           "2289a3da1c7b29efe11cec518659be24"),
            },
        },
    },
}


class _Reader:
    """The NAR byte stream - length-prefixed, 8-byte padded."""

    def __init__(self, data: bytes):
        self.data, self.pos = data, 0

    def word(self) -> str:
        length = struct.unpack_from("<Q", self.data, self.pos)[0]
        self.pos += 8
        value = self.data[self.pos:self.pos + length]
        self.pos += length + (-length % 8)
        return value.decode("utf-8")

    def blob(self) -> bytes:
        length = struct.unpack_from("<Q", self.data, self.pos)[0]
        self.pos += 8
        value = self.data[self.pos:self.pos + length]
        self.pos += length + (-length % 8)
        return value


def _expect(reader: _Reader, want: str) -> None:
    got = reader.word()
    if got != want:
        raise ValueError(f"malformed NAR: expected {want!r}, read {got!r}")


def _node(reader: _Reader, path: str) -> None:
    _expect(reader, "(")
    _expect(reader, "type")
    kind = reader.word()
    if kind == "regular":
        word, executable = reader.word(), False
        if word == "executable":
            reader.blob()
            executable, word = True, reader.word()
        if word != "contents":
            raise ValueError(f"malformed NAR: expected contents, read {word!r}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(reader.blob())
        os.chmod(path, 0o555 if executable else 0o444)
        _expect(reader, ")")
    elif kind == "symlink":
        _expect(reader, "target")
        target = reader.word()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if os.path.lexists(path):
            os.unlink(path)
        os.symlink(target, path)
        _expect(reader, ")")
    elif kind == "directory":
        os.makedirs(path, exist_ok=True)
        while True:
            word = reader.word()
            if word == ")":
                return
            if word != "entry":
                raise ValueError(f"malformed NAR: expected entry, read {word!r}")
            _expect(reader, "(")
            _expect(reader, "name")
            name = reader.word()
            _expect(reader, "node")
            _node(reader, os.path.join(path, name))
            _expect(reader, ")")
    else:
        raise ValueError(f"unsupported NAR node type {kind!r}")


def unpack_nar_data(raw: bytes, dest: str) -> None:
    """One decompressed NAR's single root node, written at `dest`. Split
    from `unpack_nar` for UX-927, whose closures are `zstd`: the reader
    is the same, only the decompressor in front of it differs."""
    reader = _Reader(raw)
    _expect(reader, "nix-archive-1")
    _node(reader, dest)


def unpack_nar(compressed: bytes, dest: str) -> None:
    """One `.nar.xz`'s single root node, written at `dest`."""
    unpack_nar_data(lzma.decompress(compressed), dest)


def fetch(url: str, sha256: str, cache_dir: str) -> bytes:
    """The pinned `.nar.xz`, from `cache_dir` when its digest already
    matches, else downloaded and cached. A digest that disagrees is a
    hard error either way: a pin nothing verifies is a host fact again."""
    cached = os.path.join(cache_dir, sha256 + ".nar.xz")
    if os.path.exists(cached):
        with open(cached, "rb") as handle:
            data = handle.read()
        if hashlib.sha256(data).hexdigest() == sha256:
            return data
    if not url.startswith(("https:", "file:")):
        raise ValueError(f"{url}: only https (the cache) and file (tests) are fetched")
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256:
        raise ValueError(f"{url}: sha256 {digest}, pinned {sha256}")
    os.makedirs(cache_dir, exist_ok=True)
    with open(cached, "wb") as handle:
        handle.write(data)
    return data


def host_arch(arch: Optional[str] = None) -> dict:
    """This machine's pin group. Never falls back to another arch: a
    wrong-arch `make` staged into the sysroot is not a degraded example,
    it is a sandbox whose every recipe fails to exec."""
    arch = arch or platform.machine()
    if arch not in PINS:
        raise SystemExit(
            f"nix_store_fetch: no pinned toolchain for {arch!r} "
            f"(pinned: {', '.join(sorted(PINS))}) - "
            f"stage_cpp_toolchain.sh is x86_64-only today (UX-915)")
    return PINS[arch]


def sysroot_lib_dir(dest: str, group: dict) -> str:
    """Where `dest` really keeps glibc, read off the one staged copy of
    the dynamic linker rather than assumed. `stage_cpp_toolchain.sh`
    resolves symlink chains lexically, so on a usrmerged host the real
    file lands under `/lib/...` while `/usr/lib/...` holds only the
    link-time files - a hardcoded guess picks the wrong one."""
    found = [os.path.join(root, group["loader"])
             for root, _dirs, files in os.walk(dest)
             if group["loader"] in files
             and not os.path.islink(os.path.join(root, group["loader"]))]
    if len(found) != 1:
        raise SystemExit(
            f"nix_store_fetch: expected exactly one real {group['loader']} "
            f"under {dest}, found {len(found)}: {found}")
    return os.path.dirname(found[0])


def stage_interpreter_link(dest: str, group: dict) -> str:
    """The one symlink that answers the pinned binaries' absolute Nix
    interpreter *and* RUNPATH, pointing at the glibc this sysroot
    already stages. Relative, not absolute: inside the sandbox both
    read the same, but a relative link also resolves inside `dest` on
    the staging host, which is what lets the script verify the staged
    make by running it before any sandbox exists."""
    link = dest + group["interpreter_dir"]
    os.makedirs(os.path.dirname(link), exist_ok=True)
    if os.path.lexists(link):
        os.unlink(link)
    os.symlink(os.path.relpath(sysroot_lib_dir(dest, group),
                               os.path.dirname(link)), link)
    return link


#: UX-916: the stable name an element selects a staged make by, so a
#: `.bst` file names a version series rather than a pin's own hash.
ALIAS_ROOT = "/usr/lib/bga-make"


def alias_path(name: str) -> str:
    """`make-4.2` -> `/usr/lib/bga-make/4.2/make`."""
    return os.path.join(ALIAS_ROOT, name.split("-", 1)[1], "make")


def stage_alias(dest: str, pin: dict) -> str:
    """The series alias for one staged pin, relative for the same
    reason `stage_interpreter_link`'s link is."""
    link = dest + alias_path(pin["name"])
    os.makedirs(os.path.dirname(link), exist_ok=True)
    if os.path.lexists(link):
        os.unlink(link)
    os.symlink(os.path.relpath(dest + pin["store_path"] + "/bin/make",
                               os.path.dirname(link)), link)
    return link


def stage(dest: str, names=None, arch: Optional[str] = None,
          cache_dir: Optional[str] = None) -> list:
    """Each named pin unpacked under `dest` at its own absolute store
    path, with its series alias, plus the interpreter link. Returns the
    pin records staged."""
    group = host_arch(arch)
    cache_dir = cache_dir or os.path.join(
        os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"),
        "bga", "nix-store")
    staged = []
    for name in names or sorted(group["paths"]):
        pin = group["paths"][name]
        target = dest + pin["store_path"]
        if not os.path.isdir(target):
            unpack_nar(fetch(pin["url"], pin["sha256"], cache_dir), target)
        record = dict(pin, name=name)
        stage_alias(dest, record)
        staged.append(record)
    stage_interpreter_link(dest, group)
    return staged


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("dest", help="the sysroot root to stage under")
    parser.add_argument("--pin", action="append", dest="names",
                        help="pin name (default: every pin for this arch)")
    parser.add_argument("--arch", default=None)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--interpreter-dir", action="store_true",
                        help="print this arch's interpreter dir and stage nothing")
    args = parser.parse_args(argv)
    if args.interpreter_dir:
        print(host_arch(args.arch)["interpreter_dir"])
        return 0
    for pin in stage(args.dest, args.names, args.arch, args.cache_dir):
        print(f"{pin['name']}\t{pin['store_path']}\t{pin['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
