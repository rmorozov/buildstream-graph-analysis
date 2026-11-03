"""UX-1373: the hook and spine a `BGA_HOOK=prebuilt` wheel carries, and whether they may be used.

Stdlib only: `setup.py` loads this file by path inside an isolated build
that has neither the package nor its dependencies. A prebuilt binary is
used only while the stamp's sha256 of its source matches the source
shipped beside it and the machine matches the one it was built on, so a
stale binary is never loaded (UX-11).
"""

import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PREBUILT_DIR = os.path.join(HERE, "prebuilt")
STAMP = "stamp.json"
SOURCES = {"hook.so": "hook.c", "spine": "spine.c"}
# UX-1374: `$CC` first, then these in order; any of them builds both.
CANDIDATES = ("cc", "gcc", "clang")
# (e_machine, EI_CLASS, EI_DATA) by `platform.machine()`: a cross or `-mx32` `$CC` exits 0, so the binary is asked.
ELF_TARGET = {
    "x86_64": (62, 2, 1),
    "aarch64": (183, 2, 1),
    "i686": (3, 1, 1),
    "armv7l": (40, 1, 1),
    "riscv64": (243, 2, 1),
    "ppc64le": (21, 2, 1),
    "s390x": (22, 2, 2),
}


def elf_target(path: str):
    """The ELF header's (e_machine, EI_CLASS, EI_DATA), or None when the file is not ELF."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(20)
    except OSError:
        return None
    if len(head) < 20 or head[:4] != b"\x7fELF" or head[5] not in (1, 2):
        return None
    return int.from_bytes(head[18:20], "little" if head[5] == 1 else "big"), head[4], head[5]


def runs_here(path: str) -> bool:
    expected = ELF_TARGET.get(platform.machine())
    return expected is not None and elf_target(path) == expected


def compiler(environ=None):
    """The compiler argv: `$CC` split like a shell word list, else the first of CANDIDATES on PATH.

    A `$CC` that does not resolve is (None, reason), never a silent fall back to another compiler.
    """
    environ = os.environ if environ is None else environ
    named = shlex.split(environ.get("CC", ""))
    if named:
        path = shutil.which(named[0], path=environ.get("PATH"))
        return ([path, *named[1:]], None) if path else (None, f"CC={environ['CC']!r} is not on PATH")
    for name in CANDIDATES:
        path = shutil.which(name, path=environ.get("PATH"))
        if path:
            return [path], None
    return None, f"no C compiler ({'/'.join(CANDIDATES)}) found on PATH"


def hook_argv(cc: list, out: str, source_dir: str = HERE) -> list:
    # -ldl for UX-46's dlsym(RTLD_NEXT): needed before glibc 2.34, harmless after.
    return [*cc, "-shared", "-fPIC", "-O2", "-Wall", "-Wextra", "-o", out, os.path.join(source_dir, "hook.c"), "-ldl"]


def spine_argv(cc: list, out: str, source_dir: str = HERE) -> list:
    # UX-106: static, because a sandbox may have no dynamic loader at all.
    return [*cc, "-static", "-O2", "-Wall", "-Wextra", "-o", out, os.path.join(source_dir, "spine.c")]


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read_stamp(prebuilt_dir=None):
    try:
        with open(os.path.join(prebuilt_dir or PREBUILT_DIR, STAMP)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def find(name: str, prebuilt_dir=None, source_dir=HERE):
    """The prebuilt `hook.so` or `spine`, or None: absent, built elsewhere, or older than its source."""
    prebuilt_dir = prebuilt_dir or PREBUILT_DIR
    stamp = read_stamp(prebuilt_dir)
    path = os.path.join(prebuilt_dir, name)
    if stamp is None or stamp.get("machine") != platform.machine() or not runs_here(path):
        return None
    source = os.path.join(source_dir, SOURCES[name])
    if not os.path.isfile(source) or stamp.get("sources", {}).get(SOURCES[name]) != sha256(source):
        return None
    return path


def build(dest: str, cc: list, source_dir: str = HERE) -> dict:
    """Compile both into `dest` and stamp them; any compile failure raises, so a wheel never ships half."""
    os.makedirs(dest, exist_ok=True)
    for argv in (
        hook_argv(cc, os.path.join(dest, "hook.so"), source_dir),
        spine_argv(cc, os.path.join(dest, "spine"), source_dir),
    ):
        result = subprocess.run(argv, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"BGA_HOOK=prebuilt: {' '.join(argv)} failed:\n{result.stderr}")
        out = argv[argv.index("-o") + 1]
        if not runs_here(out):
            raise RuntimeError(
                f"BGA_HOOK=prebuilt: {' '.join(cc)} built {os.path.basename(out)} as ELF "
                f"(machine, class, data) {elf_target(out)}, not this {platform.machine()} host; cross wheels are not supported"
            )
    version = subprocess.run([*cc, "--version"], capture_output=True, text=True).stdout.splitlines()
    stamp = {
        "machine": platform.machine(),
        "compiler": version[0] if version else " ".join(cc),
        "sources": {src: sha256(os.path.join(source_dir, src)) for src in SOURCES.values()},
    }
    with open(os.path.join(dest, STAMP), "w") as fh:
        json.dump(stamp, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return stamp
