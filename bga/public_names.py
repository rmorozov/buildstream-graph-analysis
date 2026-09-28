"""UX-1065: the public name list for a declared junction, read offline.

A public checkout on disk at a named tag, never the working tree - an
uncommitted addition to the fork must not pass through as public. The
element path comes from that tag's `project.conf`, read by
`read_scalar_key`'s own tolerant rule (`tools/bst_native_build_tracer.py`)
so a nonstandard layout is not silently missed.
"""
import os
import subprocess
import tempfile

from .tools_dispatch import _import_tool


class PublicNamesError(Exception):
    """A declared public junction whose checkout or tag `bga` cannot read."""


def _git(checkout: str, args: list) -> str:
    result = subprocess.run(["git", "-C", checkout, *args],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise PublicNamesError(
            f"{checkout}: git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _element_path(checkout: str, tag: str) -> str:
    """The tagged `project.conf`'s `element-path`, or the default."""
    text = _git(checkout, ["show", f"{tag}:project.conf"])
    read_scalar_key = _import_tool("tools.bst_native_build_tracer").read_scalar_key
    fd, path = tempfile.mkstemp(suffix=".conf")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        return read_scalar_key(path, "element-path") or "elements"
    finally:
        os.unlink(path)


def names_for(junction: str, spec: dict) -> set:
    """`{"<junction>:<path>.bst", ...}` for one declared junction.

    Read from `git ls-tree <tag>` at the declared checkout - the tag's
    tree, never the working tree - under the tag's `element-path`.
    """
    checkout, tag = spec["checkout"], spec["tag"]
    _git(checkout, ["rev-parse", f"{tag}^{{commit}}"])  # refuse a tag that is not there
    element_path = _element_path(checkout, tag)
    prefix = element_path.rstrip("/") + "/"
    listing = _git(checkout, ["ls-tree", "-r", "--name-only", tag, "--", element_path])
    passed = set()
    for line in listing.splitlines():
        if not line.endswith(".bst"):
            continue
        relative = line[len(prefix):] if line.startswith(prefix) else line
        passed.add(f"{junction}:{relative}")
    return passed


def public_names(declared: dict) -> tuple:
    """`(names, manifest_entries)` over every declared junction.

    `names` is the full pass-through set; `manifest_entries` is
    `[{"junction", "tag", "names_passed"}]`, the export's own account of
    which junctions passed and how many names each one carried.
    """
    names, entries = set(), []
    for junction, spec in declared.items():
        found = names_for(junction, spec)
        names.update(found)
        entries.append({"junction": junction, "tag": spec["tag"], "names_passed": len(found)})
    return names, entries
