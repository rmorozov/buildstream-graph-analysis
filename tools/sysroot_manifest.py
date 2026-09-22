#!/usr/bin/env python3
"""UX-914: the examples' sysroot as two declared axes, not one host.

`stage_cpp_toolchain.sh` copies this host's binaries in at their
absolute paths, so what the examples measure was decided by whichever
machine staged them and nothing said which. This says which: one row
per package, its axis, where it came from, and the version the
sysroot's own copy reports when run.

The axes are independent. The **runtime** - glibc, the shell,
coreutils, `make` - is what `style_for_make_version` reads (UX-874);
the **toolchain** - gcc, binutils, cmake and the headers that travel
with them - is what a cross toolchain would replace (UX-925). A pin on
one costs nothing on the other: `make` is pinned from
`cache.nixos.org` (UX-915) while gcc stays this host's.

Why per-package rather than a base image: UX-914's A1-A4 each need a
mirror refused at CONNECT from the dev container (four hosts, all 000,
re-measured 2026-09-22), so a component becomes a pin when its version
is shown to decide a reading, not all at once.

`--check` is two verdicts: a **pinned** row that disagrees is a broken
mechanism and exits 1; a **host** row that disagrees is a different,
working host, so it warns and
`tests/unit/test_the_sysroot_declares_both_axes.py` reddens.
"""
import argparse
import os
import subprocess
import sys
from typing import Optional

from tools import nix_store_fetch

AXES = ("runtime", "toolchain")

#: The packages `stage_cpp_toolchain.sh` takes off the staging host.
#: `binaries` are the sysroot-absolute paths this package owns out of
#: the script's own axis arrays; `probe` the one whose `--version` the
#: sysroot can be asked, relative to the sysroot root, or `None` with a
#: `why`. `version` is what this repository declares, at the upstream
#: precision Ubuntu 24.04 freezes - the release's own patch suffix
#: (`13.3.0-6ubuntu2~24.04.1`) moves without the program moving.
HOST_COMPONENTS = (
    {"name": "glibc", "axis": "runtime", "version": "2.39",
     "binaries": (), "lib_probe": "libc.so.6"},
    {"name": "coreutils", "axis": "runtime", "version": "9.4",
     "binaries": ("/usr/bin/env", "/usr/bin/uname", "/usr/bin/sort",
                  "/usr/bin/cat")},
    {"name": "dash", "axis": "runtime", "version": None,
     "binaries": ("/usr/bin/sh",), "unreadable": ("/usr/bin/sh",),
     "why": "dash answers no --version, so the sysroot cannot state it"},
    {"name": "gcc", "axis": "toolchain", "version": "13.3.0",
     "binaries": ("/usr/bin/gcc", "/usr/bin/g++", "/usr/bin/cc",
                  "/usr/bin/c++")},
    {"name": "binutils", "axis": "toolchain", "version": "2.42",
     "binaries": ("/usr/bin/ld", "/usr/bin/ld.bfd", "/usr/bin/as",
                  "/usr/bin/ar", "/usr/bin/ranlib", "/usr/bin/nm",
                  "/usr/bin/strip")},
    {"name": "cmake", "axis": "toolchain", "version": "3.28.3",
     "binaries": ("/usr/bin/cmake",)},
)


def components(arch: Optional[str] = None) -> list:
    """Every declared row: the host packages above plus one per nix
    pin, read out of `nix_store_fetch.PINS` rather than restated, so a
    pin bump cannot drift from this table."""
    rows: list[dict] = [dict(row, origin="host") for row in HOST_COMPONENTS]
    for name, pin in sorted(nix_store_fetch.host_arch(arch)["paths"].items()):
        alias = nix_store_fetch.alias_path(name)
        # `/usr/bin/make` - what an element resolves by default - is the
        # 4.4 alias's own target, so that pin owns both names.
        owned = (alias,) if name != "make-4.4" else ("/usr/bin/make", alias)
        rows.append({"name": name, "axis": "runtime", "origin": "pinned",
                     "binaries": owned,
                     "version": pin["version"].rsplit(" ", 1)[-1],
                     "store_path": pin["store_path"]})
    return rows


def declared_version_token(line: str) -> str:
    """The version out of a `--version` first line: its last token,
    without a trailing period. One rule for all six formats - gcc's
    `) 13.3.0`, cmake's `version 3.28.3`, binutils' and coreutils'
    `) N`, glibc's `version 2.39.`, make's `GNU Make 4.4.1`."""
    return line.split()[-1].rstrip(".")


def probe_labels(arch: Optional[str] = None) -> list:
    """`(row, label)` per version the sysroot can be asked for - **every**
    owned binary, not one standing in for its package. Asking `env` and
    declaring `cat` answered is a proxy, and one binary of a package can
    be the host's while its siblings are not (`/usr/bin/make` over the
    4.4 pin is exactly that). Pure, so a clone can read it with no
    sysroot staged; `probes` turns each label into an argv."""
    found = []
    for row in components(arch):
        if row.get("lib_probe"):
            found.append((row, row["lib_probe"]))
        found.extend((row, path) for path in row["binaries"]
                     if path not in row.get("unreadable", ()))
    return found


def probes(dest: str, arch: Optional[str] = None) -> list:
    """`(row, label, argv)` for each of `probe_labels`. A pinned binary
    names an absolute Nix interpreter, so it runs through the staged
    loader the way `stage_cpp_toolchain.sh` verifies its own make; a
    host binary names this host's, which `dest` stages at the same
    absolute path. glibc is asked through the one real copy of the
    loader `nix_store_fetch.sysroot_lib_dir` finds, because the staging
    script's lexical symlink resolution decides where that lands."""
    group = nix_store_fetch.host_arch(arch)
    loader = os.path.join(dest + group["interpreter_dir"], group["loader"])
    found = []
    for row, label in probe_labels(arch):
        if label == row.get("lib_probe"):
            argv = [os.path.join(nix_store_fetch.sysroot_lib_dir(dest, group),
                                 label), "--version"]
        elif row["origin"] == "pinned":
            argv = [loader, dest + label, "--version"]
        else:
            argv = [dest + label, "--version"]
        found.append((row, label, argv))
    return found


def measure(dest: str, arch: Optional[str] = None) -> dict:
    """`{label: version}` for every probe. One that cannot run is
    recorded as its own error string rather than raising, so `--check`
    names every divergence at once."""
    measured = {}
    for _row, label, argv in probes(dest, arch):
        try:
            result = subprocess.run(argv, capture_output=True, text=True,
                                    timeout=60)
        except OSError as error:
            measured[label] = f"did not run: {error}"
            continue
        if result.returncode != 0:
            measured[label] = f"exit {result.returncode}: {result.stderr.strip()}"
            continue
        first = result.stdout.splitlines()
        measured[label] = (declared_version_token(first[0]) if first
                           else "exit 0 and said nothing")
    return measured


def divergences(dest: str, arch: Optional[str] = None,
                measured: Optional[dict] = None) -> list:
    """`(origin, label, declared, measured)` per probe that disagrees.
    `measured` is threaded through so one `--check` probes each binary
    once rather than once per caller."""
    measured = measure(dest, arch) if measured is None else measured
    return [(row["origin"], label, row["version"], measured[label])
            for row, label in probe_labels(arch)
            if measured[label] != row["version"]]


def _report(dest: str, arch: Optional[str], measured: dict) -> None:
    labels = {}
    for row, label in probe_labels(arch):
        labels.setdefault(row["name"], []).append(label)
    for axis in AXES:
        print(f"{axis}:")
        for row in components(arch):
            if row["axis"] != axis:
                continue
            read = sorted({measured[label] for label in labels.get(row["name"], ())})
            state = ", ".join(read) if read else row.get("why", "")
            print(f"  {row['name']:<10} {row['origin']:<7} "
                  f"{state}  ({len(labels.get(row['name'], ()))} probed, "
                  f"{len(row['binaries'])} staged)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("dest", help="the staged sysroot's root")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 on a pinned divergence, warn on a host one")
    parser.add_argument("--arch", default=None)
    args = parser.parse_args(argv)
    measured = measure(args.dest, args.arch)
    _report(args.dest, args.arch, measured)
    if not args.check:
        return 0
    found = divergences(args.dest, args.arch, measured)
    pinned = [row for row in found if row[0] == "pinned"]
    host = [row for row in found if row[0] == "host"]
    for _origin, name, declared, got in host:
        print(f"sysroot_manifest: {name} is {got}, declared {declared} - this "
              f"host is not the one the examples' figures were measured on. "
              f"Re-declare HOST_COMPONENTS and re-derive them (UX-914).",
              file=sys.stderr)
    for _origin, name, declared, got in pinned:
        print(f"sysroot_manifest: pinned {name} is {got}, declared "
              f"{declared} - the pin did not take.", file=sys.stderr)
    return 1 if pinned else 0


if __name__ == "__main__":
    sys.exit(main())
