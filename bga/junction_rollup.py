"""UX-1327: one run rolled up by junction prefix, Plane 1 only.

An element's prefix is everything before the last `:` of its full name;
the top project's elements have none. Each element counts under its
deepest prefix only, and every ancestor prefix is a row of its own.
Built means the element ran a BUILD task in this run; cached is the
remainder, the convention `cache_effectiveness` already uses.
A bump's blast is every element behind the prefix, nested ones
included, plus their downstream closure over every graph edge.
"""

import re
from fractions import Fraction
from pathlib import Path
from typing import Optional

from .sources import is_building_kind

TOP_PROJECT_FALLBACK = "(top project)"

# The finding: a junction this many points below the top project's hit share, over at least this many elements.
HIT_SHARE_GAP = Fraction(1, 2)
MIN_ELEMENTS = 5

_NAME = re.compile(r"^name:\s*['\"]?([^'\"#\s]+)", re.MULTILINE)


def prefix_of(uid: str) -> str:
    return uid.rpartition(":")[0]


def project_name(loaded_from: Optional[str]) -> Optional[str]:
    """`project.conf`'s `name:` from the project enclosing the run directory, or None."""
    if not loaded_from:
        return None
    from .run_store import project_root

    root = project_root(str(Path(loaded_from)))
    if root is None:
        return None
    try:
        match = _NAME.search((Path(root) / "project.conf").read_text(encoding="utf-8"))
    except OSError:
        return None
    return match.group(1) if match else None


def _downstream(seeds: set, successors: dict) -> set:
    seen, stack = set(seeds), list(seeds)
    while stack:
        for nxt in successors.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def _hit_share(row: dict) -> Optional[float]:
    return row["cached"] / row["elements"] if row["elements"] else None


def compute_by_junction(graph, tasks, critical_path_detail, top_name: Optional[str] = None) -> Optional[dict]:
    """The block, or None when no element carries a junction prefix."""
    uids = [e.uid for e in getattr(graph, "elements", None) or []]
    if not any(":" in uid for uid in uids):
        return None
    kinds = {e.uid: e.element_kind for e in graph.elements}
    build_us: dict[str, int] = {}
    for task in tasks or []:
        if getattr(task.task_key.task_kind, "value", "") == "BUILD":
            uid = task.task_key.element_uid
            build_us[uid] = build_us.get(uid, 0) + task.dur_us
    path_us = {row["element_uid"]: row.get("duration_us") or 0 for row in critical_path_detail or []}
    path_total = sum(path_us.values())
    successors: dict[str, list[str]] = {}
    for dep in graph.dependencies or []:
        successors.setdefault(dep.predecessor, []).append(dep.successor)

    prefixes = {""}
    for uid in uids:
        parts = prefix_of(uid).split(":") if ":" in uid else []
        prefixes.update(":".join(parts[:i]) for i in range(1, len(parts) + 1))
    rows = []
    for prefix in sorted(prefixes, key=lambda p: p.split(":") if p else []):
        own = [uid for uid in uids if prefix_of(uid) == prefix]
        building = sum(1 for uid in own if is_building_kind(kinds.get(uid)))
        built = sum(1 for uid in own if uid in build_us)
        on_path = sum(path_us.get(uid, 0) for uid in own)
        behind = {uid for uid in uids if uid.startswith(prefix + ":")} if prefix else set()
        rows.append(
            {
                "prefix": prefix,
                "name": prefix or (top_name or TOP_PROJECT_FALLBACK),
                "depth": prefix.count(":") + 1 if prefix else 0,
                "elements": len(own),
                "building": building,
                "assembling": len(own) - building,
                "built": built,
                "cached": len(own) - built,
                "build_us": sum(build_us.get(uid, 0) for uid in own),
                "critical_path_us": on_path,
                "critical_path_share": on_path / path_total if path_total else None,
                "bump_blast_elements": len(_downstream(behind, successors)) if prefix else None,
            }
        )
    return {"graph_elements": len(uids), "critical_path_us": path_total, "rows": rows}


def cache_gaps(block: Optional[dict]) -> list[dict]:
    """Junction rows whose hit share sits `HIT_SHARE_GAP` or more below the top project's, worst first."""
    rows = (block or {}).get("rows") or []
    top = next((row for row in rows if not row["prefix"]), None)
    if not top or not top["elements"]:
        return []
    top_exact = Fraction(top["cached"], top["elements"])
    gaps = []
    for row in rows:
        if not row["prefix"] or row["elements"] < MIN_ELEMENTS:
            continue
        if top_exact - Fraction(row["cached"], row["elements"]) >= HIT_SHARE_GAP:
            gaps.append({"row": row, "hit_share": _hit_share(row), "top_hit_share": _hit_share(top)})
    return sorted(gaps, key=lambda gap: (gap["hit_share"], gap["row"]["prefix"]))
