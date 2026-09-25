#!/usr/bin/env python3
"""UX-925: the toolchain axis, pinned at its own `/nix/store` prefix.

`UX-914` left gcc, binutils and cmake as whatever the staging host
installed. Nothing here is relocated to fix that: the stock closure
stays at `/nix/store/<hash>`, content-address intact (`UX-927` stages
it, `UX-925` ruled patchelf out), and the *invocation* moves instead -
`-B` per prefix and `--sysroot`, delivered as a PATH shim (`UX-930`).

`-B` is **five** directories for a closure, not `UX-930`'s three: gcc's
libexec and libdir, `gcc-14.3.0-lib` for `libstdc++.so` and
`libgcc_s`, binutils' `bin` for `as` and `ld`, and glibc's `lib` for
the start files. Measured: without the third, `ld` cannot find
`-lgcc_s`; without the fourth, `-print-prog-name=as` answers `as`.

Only the three roots are declared by hash. The other two prefixes are
located by a mark file no other staged path has, and a mark matched
twice or not at all is `None`, which `toolchain_params --shim`
refuses - `-B` at a directory with no `cc1` is the silent case.

The pinned gcc bakes glibc's own `lib64/ld-linux-x86-64.so.2` into
every binary it links, so the closure's real glibc replaces
`UX-915`'s interpreter symlink. The runtime axis' declared rows are
untouched: the host-staged `sh`, coreutils and their glibc still load
through the tree's own `/lib64`.
"""
import argparse
import glob
import os
import platform
import sys

from tools import nix_closure, nix_store_fetch

#: Per `platform.machine()`, the store paths this repository pins for
#: the toolchain axis and the version each declares. Identified by
#: `References`, never by the name: the channel carries four
#: `gcc-14.3.0` and four `binutils-2.44` paths and the name says
#: nothing (the trap `UX-915` hit with `make`). These three all
#: reference `7nbi22pcc...-glibc-2.40-224`, the x86_64 glibc the
#: `make` pins name. `i7mdvml...` is the x86_64-only binutils;
#: `c6dssyv...` is the all-targets build, 24 more `<arch>-as` binaries
#: for targets no example has.
TOOLCHAIN_PINS = {
    "x86_64": {
        "gcc": {"version": "14.3.0", "axis": "toolchain",
                "store_path": ("/nix/store/ipr6y28viyqkhkg58rdvy27m01q5j5nh"
                               "-gcc-14.3.0"),
                "binaries": ("/usr/bin/gcc", "/usr/bin/g++", "/usr/bin/cc",
                             "/usr/bin/c++"),
                # `-nostdinc` because the pin's `cc1` has no compiled-in
                # include path: asked bare it prints its version and then
                # exits 1 on `stdc-predef.h`, which reads as a pin that
                # did not take. Ubuntu's answers 0, which is the host
                # fact this row is removing.
                "helpers": {"cc1": ("-nostdinc -version", "stderr"),
                            "cc1plus": ("-nostdinc -version", "stderr"),
                            "collect2": ("--version", "stderr")}},
        "binutils": {"version": "2.44", "axis": "toolchain",
                     "store_path": ("/nix/store/i7mdvmliqcb5lz0nqija8rq55vws"
                                    "6gi8-binutils-2.44"),
                     "binaries": ("/usr/bin/ld", "/usr/bin/ld.bfd",
                                  "/usr/bin/as", "/usr/bin/ar",
                                  "/usr/bin/ranlib", "/usr/bin/nm",
                                  "/usr/bin/strip")},
        "cmake": {"version": "4.1.2", "axis": "toolchain",
                  "store_path": ("/nix/store/i5zf2arkflazjnxv2y46fmhyfwzl5hdy"
                                 "-cmake-4.1.2"),
                  "binaries": ("/usr/bin/cmake",)},
    },
    # UX-1009: CodSpeed's Graviton runner (the only real-core host
    # available) is aarch64. Roots only - `stage_closure` reads each
    # narinfo's own `NarHash` at fetch time, so no NAR digest is pinned
    # here. Identified by `References` the same way as the x86_64 row:
    # all three reach `jjjpj4p9bz505ac1c747f2j5z3xw170p-glibc-2.40-224`.
    "aarch64": {
        "gcc": {"version": "14.3.0", "axis": "toolchain",
                "store_path": ("/nix/store/8ybmj60hvhl7g6kl6zhwq3zyyg4hfz5g"
                               "-gcc-14.3.0"),
                "binaries": ("/usr/bin/gcc", "/usr/bin/g++", "/usr/bin/cc",
                             "/usr/bin/c++"),
                "helpers": {"cc1": ("-nostdinc -version", "stderr"),
                            "cc1plus": ("-nostdinc -version", "stderr"),
                            "collect2": ("--version", "stderr")}},
        "binutils": {"version": "2.44", "axis": "toolchain",
                     "store_path": ("/nix/store/m02hdx6a5zqqk7v8qli96jzp6r12"
                                    "ngwv-binutils-2.44"),
                     "binaries": ("/usr/bin/ld", "/usr/bin/ld.bfd",
                                  "/usr/bin/as", "/usr/bin/ar",
                                  "/usr/bin/ranlib", "/usr/bin/nm",
                                  "/usr/bin/strip")},
        "cmake": {"version": "4.1.2", "axis": "toolchain",
                  "store_path": ("/nix/store/44fsdxj6326i871bgsdcp05c4rbnl9"
                                 "yc-cmake-4.1.2"),
                  "binaries": ("/usr/bin/cmake",)},
    },
}

#: The drivers delivered as a shim rather than a symlink, and which of
#: the pin's own binaries each one execs. `cc` and `c++` are the names
#: a bare `cmake` probe resolves, and the closure carries neither.
DRIVERS = {"gcc": "gcc", "g++": "g++", "cc": "gcc", "c++": "g++"}

#: One `-B` prefix per entry: the package that owns it, and the file
#: that locates it. `root` names a declared pin; `closure` is reached
#: through gcc's `References` and located by its mark alone.
PREFIXES = (
    {"name": "gcc-libexec", "owner": "gcc", "kind": "root",
     "mark": "libexec/gcc/*/*/cc1"},
    {"name": "gcc-libdir", "owner": "gcc", "kind": "root",
     "mark": "lib/gcc/*/*/libgcc.a"},
    {"name": "gcc-lib", "owner": None, "kind": "closure",
     "mark": "lib/libstdc++.so"},
    {"name": "binutils", "owner": "binutils", "kind": "root",
     "mark": "bin/ld.bfd"},
    {"name": "glibc", "owner": None, "kind": "closure",
     "mark": "lib/crt1.o"},
)


def pins(arch=None) -> dict:
    """This machine's pinned toolchain. Never falls back to another
    arch, for `nix_store_fetch.host_arch`'s reason."""
    arch = arch or platform.machine()
    if arch not in TOOLCHAIN_PINS:
        raise SystemExit(
            f"nix_toolchain: no pinned toolchain for {arch!r} "
            f"(pinned: {', '.join(sorted(TOOLCHAIN_PINS))}) - UX-925")
    return TOOLCHAIN_PINS[arch]


def roots(arch=None) -> list:
    """The store paths `nix_closure` closes over."""
    return [pin["store_path"] for pin in pins(arch).values()]


def _one(pattern: str):
    """The single path `pattern` matches, or `None`. Two matches are
    `None` too: a prefix chosen from an ambiguous glob is a `-B` that
    may point at the host's copy, which is the case with no symptom."""
    found = sorted(glob.glob(pattern))
    return found[0] if len(found) == 1 else None


def prefixes(dest: str, arch=None):
    """`{name: directory}` for the five `-B` prefixes, read off the
    staged tree, or `None` when no pin is staged under `dest` at all -
    which is how a host-staged tree still answers `toolchain_params`.
    Each value is absolute under `dest`."""
    dest = os.path.abspath(dest)
    pin = pins(arch)
    store = dest + nix_closure.STORE
    # The declared root decides, not a mark: a tree with *some*
    # `/nix/store` under it - the `make` pins alone, or a fixture with
    # one file in it - is not a pinned toolchain, and reading it as one
    # would answer with four `None` prefixes and no `-B` at all.
    if not os.path.isdir(dest + pin["gcc"]["store_path"]):
        return None
    found = {}
    for row in PREFIXES:
        base = (dest + pin[row["owner"]]["store_path"]
                if row["kind"] == "root" else os.path.join(store, "*"))
        mark = _one(os.path.join(base, row["mark"]))
        found[row["name"]] = None if mark is None else os.path.dirname(mark) + os.sep
    return found


def target_store_paths(dest: str, arch=None) -> set:
    """The store paths of the *target* half - glibc's own output (the
    loader and the start files) and its `dev` (the C headers) - located
    by a mark rather than by name. Everything else the closure stages is
    the toolchain's, which is how `toolchain_params` keeps `UX-914`'s
    seam once both halves sit under one `/nix/store`."""
    marks = ("lib/" + nix_store_fetch.host_arch(arch)["loader"],
             "include/stdio.h")
    found = {_one(os.path.join(dest + nix_closure.STORE, "*", mark))
             for mark in marks}
    return {os.path.dirname(os.path.dirname(path)) if path.count("/") else path
            for path in found if path is not None}


def driver_target(root: str, name: str, arch=None):
    """Where the pin keeps the driver `name` execs, under `root`.
    Declared, not probed: the shim is written on the staging host for
    the sandbox, where `root` is `/` and nothing is there to look at
    yet."""
    if name not in DRIVERS:
        return None
    return (root.rstrip(os.sep) + pins(arch)["gcc"]["store_path"]
            + "/bin/" + DRIVERS[name])


def driver_path(dest: str, name: str, arch=None):
    """The pinned driver of that name where it is really staged, or
    `None` - the staged tree's own `/usr/bin` answers then."""
    path = driver_target(dest, name, arch)
    return path if path and os.path.exists(path) else None


def glibc_store_path(dest: str, arch=None):
    """The closure's own glibc, located by the loader the pinned
    binaries name - the same file `stage` checks the interpreter
    symlink against."""
    loader = nix_store_fetch.host_arch(arch)["loader"]
    found = _one(os.path.join(dest + nix_closure.STORE, "*", "lib", loader))
    return None if found is None else os.path.dirname(os.path.dirname(found))


def library_path(dest: str) -> str:
    """Every staged store `lib` directory, for probing a pinned binary
    on the *staging* host: its `RUNPATH` is absolute and resolves only
    inside the sandbox, so the loader is told where the tree keeps
    them instead."""
    return ":".join(sorted(glob.glob(
        os.path.join(dest + nix_closure.STORE, "*", "lib"))))


def run_prefix(dest: str, arch=None) -> list:
    """The argv prefix that runs a pinned binary on the **staging**
    host, or `[]` when no closure is staged. A pinned binary names an
    absolute `/nix/store` interpreter, so exec'ing it directly is
    `ENOENT` until the sandbox mounts the tree at `/`; the staged
    loader is invoked instead, told where the tree keeps the rest.
    `argv[0]` stays the binary's own path, which is what lets gcc
    relocate its prefix into the tree."""
    store = glibc_store_path(dest, arch)
    if store is None:
        return []
    return [os.path.join(store, "lib",
                         nix_store_fetch.host_arch(arch)["loader"]),
            "--library-path", library_path(dest)]


def probe_flags(dest: str, arch=None) -> list:
    """The flags a *probe* adds and the shim never does. gcc execs
    `cc1`, `as` and `ld` itself, and each names the same absolute
    interpreter the driver does, so on the staging host every one is
    `ENOENT` - `-wrapper` puts the staged loader in front of all of
    them at once. In the sandbox the tree is at `/` and nothing needs
    it, which is why it is not baked into the shim."""
    prefix = run_prefix(dest, arch)
    return [] if not prefix else ["-wrapper", ",".join(prefix)]


def _relative_link(dest: str, link_at: str, target: str) -> str:
    """One `/usr/bin` name pointed into the closure. Relative, for
    `stage_alias`'s reason: an absolute `/nix/store` link dangles on
    the staging host, so nothing there could verify it."""
    link = dest + link_at
    os.makedirs(os.path.dirname(link), exist_ok=True)
    if os.path.lexists(link):
        os.unlink(link)
    os.symlink(os.path.relpath(dest + target, os.path.dirname(link)), link)
    return link


def shim_target(dest: str, name: str):
    """What the driver shim at `<dest>/usr/bin/<name>` really execs, or
    `None` when there is no shim there. Read off the file: the version
    probes ask the *pin's* binary, since a shim is a shell script and
    its own `/nix/store` paths resolve only in the sandbox, so a host
    driver copied over a shim would answer every probe correctly and
    change what the examples compile with."""
    path = os.path.join(dest, "usr", "bin", name)
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError):
        return None
    for line in text.splitlines():
        if line.startswith("exec '"):
            return line.split("'")[1]
    return None


def shim_divergences(dest: str, arch=None) -> list:
    """`(name, target)` per driver whose shim does not lead to the pin."""
    found = []
    for name in sorted(DRIVERS):
        want = driver_target(os.sep, name, arch)
        got = shim_target(dest, name)
        if got != want:
            found.append((name, got))
    return found


def stage(dest: str, arch=None, cache_dir=None) -> list:
    """The closure, plus one `/usr/bin` symlink per pinned binary that
    is not a driver. The drivers are shims, written by
    `toolchain_params --shim` after this runs: they need the prefixes
    this staging is what produces."""
    pin = pins(arch)
    staged = nix_closure.stage_closure(
        dest, roots(arch), cache_dir or nix_closure.default_cache_dir())
    for _name, row in sorted(pin.items()):
        for path in row["binaries"]:
            if os.path.basename(path) in DRIVERS:
                continue
            _relative_link(dest, path,
                           row["store_path"] + "/bin/" + os.path.basename(path))
    return staged


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("dest", help="the sysroot root to stage under")
    parser.add_argument("--arch", default=None)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--check-shims", action="store_true",
                        help="exit 1 unless every driver at /usr/bin is a "
                             "shim leading to the pin's own binary")
    parser.add_argument("--library-path", action="store_true",
                        help="print the staged store's lib directories and "
                             "stage nothing - what the loader is told when a "
                             "pinned binary is run on the staging host")
    parser.add_argument("--prefixes", action="store_true",
                        help="print the -B prefixes of an already staged tree")
    args = parser.parse_args(argv)
    if args.check_shims:
        found = shim_divergences(args.dest, args.arch)
        for name, target in found:
            print(f"nix_toolchain: /usr/bin/{name} execs {target!r}, not the "
                  f"pin's own binary - a driver over the shim answers every "
                  f"version probe and compiles something else (UX-925).",
                  file=sys.stderr)
        return 1 if found else 0
    if args.library_path:
        print(library_path(args.dest))
        return 0
    if args.prefixes:
        found = prefixes(args.dest, args.arch) or {}
        for row in PREFIXES:
            print(f"{row['name']}\t{found.get(row['name']) or 'not staged'}")
        return 0 if found and all(found.values()) else 1
    for fields in stage(args.dest, args.arch, args.cache_dir):
        print(f"{fields.get('Compression', 'none')}\t{fields['StorePath']}")
    for name, row in sorted(pins(args.arch).items()):
        print(f"#\t{name}\t{row['version']}\t{row['store_path']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
