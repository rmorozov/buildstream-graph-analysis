#!/usr/bin/env python3
"""UX-930: the toolchain's parameters, declared and read back.

`UX-925` parameterizes the pinned toolchain rather than relocating it:
`-B` for the exec prefix, `--sysroot` for the target parts. Every one
of gcc's path parameters falls back to a **host absolute path** when
the parameterized location is empty, and says nothing while it does
it - `-B <empty> -print-prog-name=cc1` reports the compiled-in prefix
and exits 0. So the parameter is never assumed here: each file class
is asked where the file really came from.

`toolchain` and `sysroot` are the two halves of the seam: gcc's own
helpers, `libgcc` and its internal headers travel with the driver,
the start files, `libc` and the C headers with the target. A class
answering from **outside** the staged tree exits 1 whichever half it
declares - that is the staging host deciding what the examples
measure (`UX-914`, one layer down). `mounted` is the third verdict,
for the one class no parameter reaches: see `UNREADABLE_HERE`.

Two readings the instrument owes its own name. `-print-file-name`
answers with `..` hops, so `crt1.o` comes back under the gcc libdir
and a prefix match on the raw string reads every start file as the
toolchain's; every answer is normalized first. And an include search
list is a proxy - a listed directory can hold nothing - so a header
class asks `-H` about a real `#include`.
"""
import argparse
import glob
import os
import subprocess
import sys
from typing import Optional

from tools import sysroot_manifest

TOOLCHAIN, SYSROOT, MOUNTED = "toolchain", "sysroot", "mounted"

#: One row per file class: the half of the seam that owns it, the
#: driver to ask, and the question. `program` and `file` read a path
#: back from `-print-prog-name`/`-print-file-name`. `header` names a
#: real header and reads where `-H` says it came from - not the search
#: list, whose entries are a proxy: a directory can be listed and hold
#: nothing, and the C++ entries drop out of the list silently when the
#: prefix has no `include/c++`.
CLASSES = (
    {"name": "exec-prefix", "owner": TOOLCHAIN, "driver": "gcc",
     "ask": ("program", "cc1")},
    {"name": "libgcc", "owner": TOOLCHAIN, "driver": "gcc",
     "ask": ("file", "libgcc.a")},
    {"name": "gcc-headers", "owner": TOOLCHAIN, "driver": "gcc",
     "ask": ("header", "stddef.h")},
    {"name": "start-files", "owner": SYSROOT, "driver": "gcc",
     "ask": ("file", "crt1.o")},
    # The dev `.so` is a symlink the gcc libdir owns, pointing at
    # content in the target half - so the *link* is what the search
    # answers with, and a dangling one reads as nothing rather than as
    # the host.
    {"name": "libstdc++", "owner": TOOLCHAIN, "driver": "g++",
     "ask": ("file", "libstdc++.so")},
    {"name": "c-headers", "owner": SYSROOT, "driver": "gcc",
     "ask": ("header", "stdio.h")},
    # `sysroot` is Ubuntu's answer, where libstdc++'s headers are
    # their own package under `/usr/include`. A pinned gcc carries its
    # own inside the store path, and `UX-925` flips this one word.
    {"name": "cxx-headers", "owner": SYSROOT, "driver": "g++",
     "ask": ("header", "vector")},
)

#: The directories the driver's own half lives in, relative to the
#: sysroot root. Everything else inside the tree is the target's.
TOOLCHAIN_ROOTS = ("/usr/lib/gcc", "/usr/libexec/gcc")

#: The classes this host is allowed not to be able to read, because no
#: parameter moves them and the sandbox answers them from the tree at
#: the same absolute path. `stage_cpp_toolchain.sh` stages the drivers
#: as the host's symlink chains through `/etc/alternatives`, so the
#: prefix they relocate against is the host's - the C++ header
#: directory is the one class no `-B` then reaches. A class that
#: goes the same way and is not named here exits 1, because a
#: parameter was passed for it and did not take - which is the whole
#: of what this row guards. The warning is a declaration, not a
#: ritual (`UX-914`'s two verdicts).
UNREADABLE_HERE = ("cxx-headers",)


def parameters(dest: str) -> dict:
    """The values a shim passes, derived from the staged tree rather
    than from this host. `--sysroot` is the tree's own root. `-B` is
    **three** directories, not one: measured with the driver outside
    the tree, the libexec prefix alone leaves `libgcc`, gcc's own
    headers, `libstdc++` and the C++ headers answering from the host,
    and adding the gcc libdir still leaves the start files. Each is
    read off a file only that directory has, so a tree with a
    different triple or gcc major is read rather than assumed.

    `dest` is made absolute first: a relative one produces relative
    `-B` flags, whose relative answers then sit outside the absolute
    tree and read as the host's - this row's own failure shape, from
    the inside."""
    dest = os.path.abspath(dest)
    # Each prefix is found by a file only its directory has, under
    # either layout: this host's `/usr` tree, or a pinned closure's
    # own `/nix/store/<hash>` (`UX-925`). The start files are the
    # reason both are named - in the closure they sit in **glibc's**
    # store path, not gcc's, so a `/usr/lib/*` glob alone would write
    # a `-B` short of the tree, which is the silent case.
    marks = (("libgcc", ("usr/lib/gcc/*/*/libgcc.a",
                         "nix/store/*/lib/gcc/*/*/libgcc.a")),
             ("crt1", ("usr/lib/*/crt1.o", "nix/store/*/lib/crt1.o")))
    prefixes = {}
    for name, patterns in marks:
        found = sorted(one for pattern in patterns
                       for one in glob.glob(os.path.join(dest, pattern)))
        prefixes[name] = (os.path.dirname(found[0]) + os.sep
                          if len(found) == 1 else None)
    # The exec prefix is `UX-914`'s own answer, not a second copy of
    # it: `helper_path` already locates a staged helper by name.
    cc1 = sysroot_manifest.helper_path(dest, "cc1")
    prefixes["cc1"] = None if cc1 is None else os.path.dirname(cc1) + os.sep
    return {"prefixes": prefixes, "sysroot": os.path.abspath(dest)}


def flags_for(params: dict) -> list:
    """`-B` per found prefix, then `--sysroot`. A prefix that is not in
    the tree is left out rather than passed empty - `-B` at a directory
    with no `cc1` is the silent fallback this row exists for, so it is
    never written by this code."""
    return ([f"-B{path}" for _name, path in sorted(params["prefixes"].items())
             if path is not None]
            + ["--sysroot=" + params["sysroot"]])


def _header_path(argv: list, language: str, name: str) -> Optional[str]:
    """Which search path `#include <name>` really came from, off
    `-H`'s own hierarchy - its first depth-1 line is the header
    itself. `-fno-canonical-system-headers` because the default
    answers with the file's `realpath`, and the question is which
    parameter reached it: inside the sandbox the staged tree *is* the
    path, so a resolved one reads a host that is not mounted there."""
    result = subprocess.run(argv + ["-fno-canonical-system-headers",
                                    "-E", "-H", "-x", language, "-", "-o",
                                    os.devnull],
                            input=f"#include <{name}>\n", capture_output=True,
                            text=True, timeout=60)
    for line in result.stderr.splitlines():
        if line.startswith(". ") and not line.startswith(". ."):
            return os.path.normpath(line[2:].strip())
    return None


def driver_path(row: dict, driver_root: str) -> str:
    """The driver to ask. `driver_root` is where the toolchain's own
    `bin` lives - the staged tree today, the pin's own store path when
    `UX-925` lands, and `/` for the guard that exercises the shim's
    case: a driver outside the tree, pulled into it by `-B` alone."""
    return os.path.join(driver_root, "usr", "bin", row["driver"])


def resolve(dest: str, row: dict, flags: Optional[list] = None,
            driver_root: Optional[str] = None) -> Optional[str]:
    """Where the driver really finds this class, normalized. `None`
    when it finds nothing: `-print-file-name` answers with the bare
    name it was given, and a header directory that does not exist is
    dropped from the search list without a word."""
    dest = os.path.abspath(dest)
    kind, what = row["ask"]
    if flags is None:
        flags = flags_for(parameters(dest))
    root = dest if driver_root is None else driver_root
    argv = [driver_path(row, root)] + flags
    if kind == "header":
        return _header_path(argv, "c++" if row["driver"] == "g++" else "c", what)
    flag = "-print-prog-name=" if kind == "program" else "-print-file-name="
    result = subprocess.run(argv + [flag + what], capture_output=True,
                            text=True, stdin=subprocess.DEVNULL, timeout=60)
    answer = result.stdout.strip()
    if result.returncode != 0 or not answer or answer == what:
        return None
    return os.path.normpath(answer)


def owner_of(dest: str, path: Optional[str]) -> Optional[str]:
    """`toolchain`, `sysroot`, `mounted`, or `None`.

    `mounted` is the staging host answering at an absolute path the
    staged tree *also* carries. Some of gcc's paths are absolute and
    move with neither flag - the C++ headers are one - so on this host
    they read `/usr/include/c++`, while in the sandbox, which has only
    this tree at `/`, the same path is the staged copy. That is a
    reading this host cannot take, not a broken parameter, so
    `--check` warns on it the way `sysroot_manifest` warns on a host
    row. A path the tree does **not** carry is neither: nothing
    answers it in the sandbox.
    """
    if path is None:
        return None
    root = os.path.abspath(dest)
    if root == os.sep:
        inside = path
    elif path == root or path.startswith(root + os.sep):
        inside = path[len(root):] or os.sep
    else:
        return MOUNTED if os.path.exists(root + path) else None
    return (TOOLCHAIN if any(inside.startswith(part + os.sep) or inside == part
                             for part in TOOLCHAIN_ROOTS) else SYSROOT)


def mounted_owner(dest: str, path: str) -> Optional[str]:
    """Which half the tree's own copy of an absolute `path` sits in."""
    return owner_of(dest, os.path.abspath(dest) + path)


def measure(dest: str, flags: Optional[list] = None,
            driver_root: Optional[str] = None) -> dict:
    """`{class: (path, owner)}` for every row."""
    dest = os.path.abspath(dest)
    measured = {}
    for row in CLASSES:
        path = resolve(dest, row, flags, driver_root)
        measured[row["name"]] = (path, owner_of(dest, path))
    return measured


def divergences(dest: str, measured: Optional[dict] = None) -> list:
    """`(name, declared, path, owner)` per class that does not answer
    from the half it declares. A `mounted` answer whose staged copy is
    in the declared half is left out - `unreadable_here` carries it
    instead, as a warning."""
    measured = measure(dest) if measured is None else measured
    found = []
    for row in CLASSES:
        path, owner = measured[row["name"]]
        if owner == row["owner"]:
            continue
        if (owner == MOUNTED and row["name"] in UNREADABLE_HERE
                and mounted_owner(dest, path) == row["owner"]):
            continue
        found.append((row["name"], row["owner"], path, owner))
    return found


def unreadable_here(dest: str, measured: Optional[dict] = None) -> list:
    """`(name, path)` per class this host cannot read, because the
    parameter does not reach it and the absolute path it answers is
    the host's own copy of what the sandbox mounts from the tree."""
    dest = os.path.abspath(dest)
    measured = measure(dest) if measured is None else measured
    return [(row["name"], measured[row["name"]][0]) for row in CLASSES
            if measured[row["name"]][1] == MOUNTED
            and row["name"] in UNREADABLE_HERE
            and mounted_owner(dest, measured[row["name"]][0]) == row["owner"]]


def shim_text(driver: str, params: dict) -> str:
    """The PATH shim, as text. Shell-only (`UX-918`: the sandbox stages
    no `dirname` or `basename`), `exec` (one more `execve`, no extra
    process - measured 16 to 17 on a `#include <stdio.h>` link), and
    the parameters baked in rather than read from the environment, so
    there is no `PATH` search past this file and `UX-846`'s recursion
    hazard cannot arise."""
    flags = flags_for(params)
    for value in [driver] + flags:
        if "'" in value:
            raise ValueError(f"a single quote in {value!r} would break the shim")
    quoted = " ".join(f"'{flag}'" for flag in flags)
    return ("#!/bin/sh\n"
            "# UX-930: the driver, with its parameters baked in. Neither\n"
            "# flag is loud when it is wrong, so toolchain_params --check\n"
            "# reads back where each file class actually came from.\n"
            f"exec '{driver}' {quoted} \"$@\"\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("dest", help="the staged sysroot's root")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 on a class answering from outside the tree")
    parser.add_argument("--shim", metavar="DRIVER",
                        help="write this driver's shim to stdout instead")
    parser.add_argument("--driver-root", default=None,
                        help="where the toolchain's own bin lives, when it is "
                             "not the staged tree (default: the staged tree)")
    args = parser.parse_args(argv)
    params = parameters(args.dest)
    if args.shim:
        missing = sorted(name for name, path in params["prefixes"].items()
                         if path is None)
        if missing:
            print(f"toolchain_params: {args.dest} has no {', '.join(missing)} "
                  "- a shim written now would carry a -B short of the tree, "
                  "which is the silent case (UX-930).", file=sys.stderr)
            return 1
        root = args.driver_root or args.dest
        sys.stdout.write(shim_text(os.path.join(root, "usr", "bin", args.shim),
                                   params))
        return 0
    # The stager calls this as a hard gate, so a driver that is not
    # there names itself rather than arriving as a traceback (UX-930).
    absent = sorted({path for path in
                     (driver_path(row, args.driver_root or args.dest)
                      for row in CLASSES) if not os.path.exists(path)})
    if absent:
        print(f"toolchain_params: no driver at {', '.join(absent)} - "
              "nothing to ask, so nothing is read back (UX-930).",
              file=sys.stderr)
        return 1
    measured = measure(args.dest, driver_root=args.driver_root)
    for flag in flags_for(params):
        print(flag)
    for row in CLASSES:
        path, owner = measured[row["name"]]
        state = "not found" if path is None else f"{owner or 'HOST'}  {path}"
        print(f"  {row['name']:<12} {row['owner']:<9} {state}")
    if not args.check:
        return 0
    for name, path in unreadable_here(args.dest, measured):
        print(f"toolchain_params: {name} answers {path}, which no parameter "
              f"moves - this host cannot read it, and the sandbox answers it "
              f"from the staged tree at the same path (UX-930).",
              file=sys.stderr)
    found = divergences(args.dest, measured)
    for name, declared, path, owner in found:
        where = ("with nothing - no such name anywhere the parameters reach"
                 if path is None
                 else f"from {owner or 'this host'}, at {path}")
        print(f"toolchain_params: {name} declares {declared} and answers "
              f"{where}. Neither flag says so on its own (UX-930).",
              file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
