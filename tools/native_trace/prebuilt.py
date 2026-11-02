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
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
PREBUILT_DIR = os.path.join(HERE, "prebuilt")
STAMP = "stamp.json"
SOURCES = {"hook.so": "hook.c", "spine": "spine.c"}


def hook_argv(cc: str, out: str, source_dir: str = HERE) -> list:
    # -ldl for UX-46's dlsym(RTLD_NEXT): needed before glibc 2.34, harmless after.
    return [cc, "-shared", "-fPIC", "-O2", "-Wall", "-Wextra", "-o", out, os.path.join(source_dir, "hook.c"), "-ldl"]


def spine_argv(cc: str, out: str, source_dir: str = HERE) -> list:
    # UX-106: static, because a sandbox may have no dynamic loader at all.
    return [cc, "-static", "-O2", "-Wall", "-Wextra", "-o", out, os.path.join(source_dir, "spine.c")]


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
    if stamp is None or not os.path.isfile(path) or stamp.get("machine") != platform.machine():
        return None
    source = os.path.join(source_dir, SOURCES[name])
    if not os.path.isfile(source) or stamp.get("sources", {}).get(SOURCES[name]) != sha256(source):
        return None
    return path


def build(dest: str, cc: str, source_dir: str = HERE) -> dict:
    """Compile both into `dest` and stamp them; any compile failure raises, so a wheel never ships half."""
    os.makedirs(dest, exist_ok=True)
    for argv in (
        hook_argv(cc, os.path.join(dest, "hook.so"), source_dir),
        spine_argv(cc, os.path.join(dest, "spine"), source_dir),
    ):
        result = subprocess.run(argv, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"BGA_HOOK=prebuilt: {' '.join(argv)} failed:\n{result.stderr}")
    version = subprocess.run([cc, "--version"], capture_output=True, text=True).stdout.splitlines()
    stamp = {
        "machine": platform.machine(),
        "compiler": version[0] if version else cc,
        "sources": {src: sha256(os.path.join(source_dir, src)) for src in SOURCES.values()},
    }
    with open(os.path.join(dest, STAMP), "w") as fh:
        json.dump(stamp, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return stamp
