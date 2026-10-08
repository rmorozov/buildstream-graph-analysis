"""UX-1347: a non-Python file under a packaged directory ships, or is named as dev-only.

`tools/native_trace/wrappers/` was missing from `package-data`, so a
`pip install .` had no wrappers and `--jobserver auto` died in bwrap.
"""

import fnmatch
import os
import pathlib

import pytest

from tools.bst_native_build_tracer import JOBSERVER_WRAPPERS_DIR

tomllib = pytest.importorskip("tomllib")  # stdlib from 3.11; the PR lane runs 3.12

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Under a packaged directory, read only from a checkout.
DEV_ONLY = {"tools/dev_run.sh"}


def _setuptools():
    with open(ROOT / "pyproject.toml", "rb") as f:
        return tomllib.load(f)["tool"]["setuptools"]


def _source_dir(package, package_dir):
    for prefix, src in package_dir.items():
        if package == prefix or package.startswith(prefix + "."):
            return os.path.join(src, *package[len(prefix) :].split(".")[1:])
    return os.path.join(*package.split("."))


def _matches(rel, glob):
    # Per component, so a subdirectory names its own glob instead of riding setuptools' deprecated pickup.
    parts, pattern = rel.split("/"), glob.split("/")
    return len(parts) == len(pattern) and all(fnmatch.fnmatchcase(a, b) for a, b in zip(parts, pattern))


def unshipped(setuptools):
    """Non-.py files under a listed package that no package-data glob of theirs matches."""
    package_dir = setuptools.get("package-dir", {})
    data = setuptools.get("package-data", {})
    sources = {p: _source_dir(p, package_dir) for p in setuptools["packages"]}
    present = sorted(
        {
            str(f.relative_to(ROOT))
            for d in set(sources.values())
            for f in (ROOT / d).rglob("*")
            if f.is_file() and "__pycache__" not in f.parts
        }
    )
    missing = []
    for path in present:
        if path.endswith(".py") or path in DEV_ONLY:
            continue
        # The deepest listed package holding the file owns its globs.
        owner = max((p for p, d in sources.items() if path.startswith(d + "/")), key=lambda p: len(sources[p]))
        rel = os.path.relpath(path, sources[owner])
        if not any(_matches(rel, g) for g in data.get(owner, [])):
            missing.append(path)
    return missing


def test_every_tracked_runtime_file_is_package_data():
    assert unshipped(_setuptools()) == []


def test_the_wrappers_are_shipped_by_their_own_glob():
    setuptools = _setuptools()
    setuptools["package-data"]["bga._tools.native_trace"] = ["*.c", "*.h"]
    wrappers = os.path.relpath(JOBSERVER_WRAPPERS_DIR, ROOT)
    assert f"{wrappers}/ninja" in unshipped(setuptools)
    assert "tools/native_trace/wrappers/flto/gcc" in unshipped(setuptools)
    setuptools["package-data"]["bga._tools.native_trace"] = ["*.c", "*.h", "wrappers/*"]
    assert unshipped(setuptools) == [
        "tools/native_trace/wrappers/flto/c++",
        "tools/native_trace/wrappers/flto/cc",
        "tools/native_trace/wrappers/flto/g++",
        "tools/native_trace/wrappers/flto/gcc",
    ]
