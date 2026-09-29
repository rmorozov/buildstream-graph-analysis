"""UX-1073: what one analysis was computed from, so a reader can reuse it.

The producer stamp, a sha256 of every input the analysis reads - each
file of the run directory, the host samples beside it, the Plane 2
report actually attached, and the sibling report whenever
`plane2.absence()` reads it; the raw log's presence - and every
result-affecting option of
`bga analyze`. A published analysis is reused only when its fingerprint
equals the one a fresh analysis would carry; an option in neither table
below makes the analysis non-reusable (`None`), never reusable.
"""
import hashlib
import os
from pathlib import Path
from typing import Optional

KEY = "fingerprint"

#: Options that change the analysis. `history_dir` enters as a digest.
RESULT = frozenset({"capacity", "replay", "heuristic", "diagnostics", "cold",
                    "allow_partial_cold", "history_dir"})
#: Options that change only the rendering, or enter as a digest term.
INERT = frozenset({"directory", "plane2", "no_plane2", "verbose", "quiet",
                   "log_file", "format", "output", "explain", "full_path",
                   "full_sources", "by_kind", "section", "help"})

_CHUNK = 1 << 20


def digest(path, cache: Optional[dict] = None) -> Optional[str]:
    """`sha256:<hex>` of one file, or None when it cannot be read."""
    key = os.path.abspath(path)
    if cache is not None and key in cache:
        return cache[key]
    hasher = hashlib.sha256()
    try:
        with open(key, "rb") as handle:
            for chunk in iter(lambda: handle.read(_CHUNK), b""):
                hasher.update(chunk)
        value: Optional[str] = "sha256:" + hasher.hexdigest()
    except OSError:
        value = None
    if cache is not None:
        cache[key] = value
    return value


def _sibling(run_dir: str, declined: bool, cache: dict):
    """The sibling report as `plane2.absence()` reads it: its content
    only when absence opens it (not declined, raw log present), else
    whether it exists - so a view never opens a report it cannot attach."""
    from . import run_store

    path = run_store.sibling_plane2(run_dir)
    if path is None:
        return None
    if declined or run_store.sibling_raw_log(run_dir) is None:
        return True
    return digest(path, cache)


def _tree(directory, cache: Optional[dict] = None) -> dict:
    """Every regular file under `directory`, by relative path."""
    root = Path(directory)
    files = sorted(p for p in root.rglob("*") if p.is_file())
    return {p.relative_to(root).as_posix(): digest(p, cache) for p in files}


def analyze_dests() -> list[str]:
    """Every option `bga analyze` parses, by its dest."""
    from .cli import create_parser

    parser = create_parser()
    for action in parser._actions:
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict) and "analyze" in choices:
            return [a.dest for a in choices["analyze"]._actions]
    return []


def attached_plane2(args) -> Optional[str]:
    """The Plane 2 report `cli.analyzed` attaches for `args`, resolved."""
    from . import plane2 as plane2_shape

    if getattr(args, "no_plane2", False):
        return None
    path = getattr(args, "plane2", None)
    if path:
        return path
    directory = getattr(args, "directory", None)
    return plane2_shape.attachable(str(directory))[0] if directory else None


def of(args, dests: Optional[list] = None) -> Optional[dict]:
    """The fingerprint of `bga analyze` under `args`, or None if not reusable."""
    from . import producer, run_store

    dests = analyze_dests() if dests is None else dests
    options = {}
    for dest in sorted(set(dests)):
        if dest in INERT:
            continue
        if dest not in RESULT:
            return None
        options[dest] = getattr(args, dest, None)
    cache: dict = {}
    if options.get("history_dir"):
        options["history_dir"] = [_tree(p, cache) for p in options["history_dir"]]
    run_dir = os.path.abspath(str(args.directory))
    beside = os.path.dirname(os.path.normpath(run_dir))
    plane2 = attached_plane2(args)
    return {
        "producer": producer.stamp(),
        "inputs": _tree(run_dir, cache),
        "beside": {
            run_store.HOST_SAMPLES_NAME:
                digest(os.path.join(beside, run_store.HOST_SAMPLES_NAME), cache),
            run_store.PLANE2_NAME: _sibling(
                run_dir, bool(getattr(args, "no_plane2", False)), cache),
            run_store.RAW_LOG_NAME: run_store.sibling_raw_log(run_dir) is not None,
        },
        "plane2": digest(plane2, cache) if plane2 else None,
        "options": options,
    }
