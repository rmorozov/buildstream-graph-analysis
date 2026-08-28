"""UX-172: `bga blast TARGET` — what rebuilds if I touch this.

`UX-171`'s table ranks the widest resources in a build. The question a
developer actually arrives with points the other way: *I am about to
change this, what does it cost?* Three shapes of "this", one answer.

- A **url** is the monorepo case: every element sourcing that
  repository, its closure, the kind split, and the measured cost.
- A **path** is the per-commit answer that content keying makes
  possible: the elements whose `local` sources stage that file or
  directory, and nothing else.
- An **element name** is the closure the tool has always been able to
  compute, printed in the same shape so the three views read alike.

This is a question, not a gate: it exits 0 on an answer of zero, the
same as on an answer of two hundred. A gate belongs in `bga compare`,
where the refusal grammar already lives.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from . import schemas
from . import sources as sources_mod
from .graph.edg import (build_element_graph, compute_element_durations,
                       compute_reachability)
from .ingest.loader import load_all
from .units import US_PER_S


# The order a target is resolved in, applied top to bottom and stated in
# the output whenever more than one shape could have matched.
RESOLUTION_ORDER = ("url", "path", "element")


def known_identity(inventory: dict, target: str) -> Optional[dict]:
    """The resource this target *is*, when the inventory already knows it.

    `UX-178`. The Shared Sources table prints the normalized, scheme-less
    identity (`gitlab.example.com/org/monorepo`), and the url detector
    below requires a scheme - so the tool's own output, pasted as its own
    input one command later, resolved as a *path* and answered "rebuilds
    nothing here" about the exact monorepo question the feature exists
    for. Observed live in round 19.

    Matching the inventory first makes the printed form round-trip by
    construction rather than by two heuristics happening to agree: what
    the report printed is what the query looks up.
    """
    if not inventory:
        return None
    candidates = {target, target.strip("/")}
    candidates.add(sources_mod.normalize_url(target))
    for resources in (inventory.get("elements") or {}).values():
        for resource in resources or []:
            identity = resource.get("identity")
            if identity and identity in candidates:
                return resource
    return None


def _stages_at_project_root(inventory: dict) -> bool:
    """Does anything stage the project root, so a bare name could be one?"""
    for resources in (inventory.get("elements") or {}).values():
        for resource in resources or []:
            if resource.get("keying") != "content":
                continue
            staged = (resource.get("identity") or "").strip("/")
            if staged in ("", "."):
                return True
    return False


def _cwd_is_inside(project_dir: Optional[str]) -> bool:
    """Is the shell standing inside the project this question is about?"""
    if not project_dir:
        return False
    try:
        return os.path.commonpath(
            [os.path.abspath(os.getcwd()), os.path.abspath(project_dir)]
        ) == os.path.abspath(project_dir)
    except ValueError:  # different drives / unrelated roots
        return False


def classify_target(target: str, project_dir: Optional[str] = None,
                    inventory: Optional[dict] = None) -> List[str]:
    """Every shape `target` could be, most specific first.

    Ambiguity is real: a project could name an element `https` (it
    could not, but a path and an element name collide easily - `lib-a`
    is a directory *and* the stem of `lib-a.bst`). The resolution order
    is fixed and the answer says which one it used, rather than the
    command silently picking.
    """
    shapes = []
    if "://" in target or target.startswith("git@") or target.endswith(".git"):
        shapes.append("url")
    # UX-182 item 3: cwd first, project root second. A developer asking
    # this question is usually `cd`'d into the component they just
    # edited, and a name their shell completed for them resolved against
    # the project root instead - so it existed nowhere, read as an
    # element name, and answered "rebuilds nothing".
    #
    # Only when cwd is *inside* the project, though: from anywhere else
    # a bare `README.md` that happens to exist beside the shell says
    # nothing about what this project stages, and reading it as a path
    # would be a different confident wrong answer.
    if os.path.isabs(target):
        candidates = [target]
    else:
        candidates = [os.path.join(project_dir or ".", target)]
        if _cwd_is_inside(project_dir):
            candidates.insert(0, os.path.abspath(target))
    # On disk, or shaped like a path. The second half matters: the
    # question is often asked about a file that was just *deleted*, or
    # typed from a diff rather than from the filesystem, and refusing
    # to read those as paths would answer "nothing sources it" about a
    # change that rebuilds half the project.
    # UX-178: a *top-level* deleted file has no `/` to recognise it by, so
    # it only reads as a path when something in this project stages the
    # root - which is the only case where a bare name could be one.
    if (any(os.path.exists(candidate) for candidate in candidates) or "/" in target
            or _stages_at_project_root(inventory or {})):
        shapes.append("path")
    if target.endswith(".bst"):
        shapes.append("element")
    if not shapes:
        # Nothing on disk and no `.bst`: still worth trying as a url and
        # as an element, in that order, so a typo'd path gets a "no
        # element of that name" rather than silence.
        shapes = ["url", "element"]
    return [shape for shape in RESOLUTION_ORDER if shape in shapes]


def _elements_for_url(inventory: dict, target: str) -> Set[str]:
    wanted = sources_mod.normalize_url(target)
    found = set()
    for uid, resources in (inventory.get("elements") or {}).items():
        for resource in resources or []:
            if resource.get("keying") == "ref" and resource.get("identity") == wanted:
                found.add(uid)
    return found


def _elements_for_path(inventory: dict, target: str, project_dir: Optional[str]) -> Set[str]:
    """Elements whose content-keyed sources stage `target`.

    A source staging `files/src` covers `files/src/lib-a/main.c`, so
    this matches a path *inside* a staged directory as well as the
    directory itself - which is the question a developer asks about a
    file they just edited.
    """
    # UX-182 item 3: a path typed from a subdirectory used to resolve
    # against the project root only, and silently miss. Try it as given
    # (relative to cwd) first, then as project-relative.
    candidates = []
    absolute = os.path.abspath(target)
    for base in ([project_dir] if project_dir and (
            os.path.isabs(target) or _cwd_is_inside(project_dir)) else []):
        try:
            candidates.append(os.path.relpath(absolute, base))
        except ValueError:
            pass
    candidates.append(target)
    relative = None
    for candidate in candidates:
        normalised = os.path.normpath(candidate).strip("/")
        if not normalised.startswith(".."):
            relative = normalised
            break
    if relative is None:
        # UX-184: no candidate stayed inside the project. Falling back to
        # the `..`-prefixed form let a `../monorepo` *identity* - which
        # the inventory no longer produces, but old `sources.json` files
        # still carry - prefix-match a query and answer confidently
        # about a path this project cannot key.
        return set()
    found = set()
    for uid, resources in (inventory.get("elements") or {}).items():
        for resource in resources or []:
            if resource.get("keying") != "content":
                continue
            identity = resource.get("identity") or ""
            if os.path.isabs(identity) or identity.startswith(".."):
                # UX-184: an inventory written before the complaint above
                # existed. Not keyable, so not matchable.
                continue
            # UX-192: a junctioned content identity is namespaced
            # (`sub.bst:files/libfoo`, UX-182), and a developer types the
            # filesystem path - so the prefix is stripped for matching.
            # The identity keeps it: it is what the table prints and what
            # `bga blast` resolves exactly.
            _junction, _colon, within = identity.rpartition(":")
            staged = os.path.normpath(within or identity).strip("/")
            if not staged:
                continue
            if relative == staged or relative.startswith(staged + "/"):
                found.add(uid)
    return found


def _kind_of(inventory: dict, direct: Set[str], keying: Optional[str]) -> Optional[str]:
    """The source kind behind a heuristic match, when it is unambiguous.

    `UX-192`. A heuristic resolves a *spelling*, not a stanza, so more
    than one kind can answer - two elements consuming one path through
    `local` and `patch`, say. One kind is reported; several are reported
    as none, and the keying sentence falls back to the keying-only
    wording rather than picking a kind at random.
    """
    kinds = {resource.get("kind")
             for uid in direct
             for resource in (inventory.get("elements") or {}).get(uid) or []
             if resource.get("keying") == keying}
    kinds.discard(None)
    return kinds.pop() if len(kinds) == 1 else None


def blast(run_dir, target: str, project_dir: Optional[str] = None,
          measure: bool = True) -> dict:
    """The answer, as data. `bga/report` decides how to say it.

    `measure=False` (`UX-182`) answers the direct/closure/kind half from
    the graph and the inventory alone. The measured half needs the full
    analysis pipeline, which on a project of thousands of elements is
    the whole `UX-168`/`UX-169` cost - paid, until now, to answer one
    lookup. The expensive half is still the default, because the cost
    is what makes the answer actionable; it is now possible to decline
    it, and the answer says the cost was not measured rather than
    reporting it as unmeasured-by-the-run.
    """
    run_dir = Path(run_dir)
    _context, graph, _trace = load_all(run_dir)
    inventory = sources_mod.load_inventory(run_dir / "sources.json") or {}
    downstream, _upstream = compute_reachability(graph)
    # UX-206: `downstream` is the transitive closure - every element a
    # change reaches, at any distance. The tree needs the *immediate*
    # consumers, or every level collapses to depth 1.
    _predecessors, successors = build_element_graph(graph)
    kinds = {e.uid: (e.element_kind or "unknown") for e in graph.elements}
    known = set(kinds)

    # UX-178: what the report printed, looked up as what the report
    # printed. Before any heuristic, because a heuristic that disagrees
    # with the tool's own output is the bug this closes.
    matched = known_identity(inventory, target)
    shapes = classify_target(target, project_dir, inventory)
    direct: Set[str] = set()
    used: Optional[str] = None
    keying = None
    kind = None
    if matched is not None:
        keying = matched.get("keying")
        kind = matched.get("kind")
        used = "url" if keying == "ref" else "path"
        # UX-192: grouped by the `(kind, identity)` pair the table groups
        # by. Matching on identity alone merged two kinds that happen to
        # share a spelling here while the table showed them apart, so the
        # two surfaces disagreed about the same run.
        key = (kind, matched.get("identity"))
        direct = {uid for uid, resources in (inventory.get("elements") or {}).items()
                  if any(sources_mod.resource_key(r) == key for r in resources or [])}
        # The other readings are still reported: an exact match decides
        # the answer, it does not hide that the name was ambiguous.
        if used not in shapes:
            shapes = [used] + shapes
    for shape in [] if direct else shapes:
        if shape == "url":
            direct = _elements_for_url(inventory, target)
            keying = "ref"
        elif shape == "path":
            direct = _elements_for_path(inventory, target, project_dir)
            keying = "content"
        else:
            direct = {target} & known
            keying = None
        if direct:
            used = shape
            kind = _kind_of(inventory, direct, keying)
            break
    if used is None:
        used = shapes[0] if shapes else "element"

    reachable: Set[str] = set(direct)
    for uid in direct:
        reachable |= set(downstream.get(uid) or ())
    building, assembling = sources_mod.split_by_kind(reachable, kinds)
    # UX-341: the durations arrive as integer microseconds and stay
    # that way. This divided them by 1e6 to publish `measured_seconds`,
    # which was a lossy downgrade of a value the tool already held
    # exactly, and put a second spelling of time in the payload.
    durations = (compute_element_durations(_tasks_of(run_dir))
                 if measure else {})
    measured = [durations[uid] for uid in reachable if uid in durations]
    by_kind: Dict[str, int] = {}
    for uid in reachable:
        by_kind[kinds.get(uid, "unknown")] = by_kind.get(kinds.get(uid, "unknown"), 0) + 1
    return {
        "blast_tree": _by_depth(direct, reachable, successors, kinds, durations),
        "target": target,
        "resolved_as": used,
        "also_matched": [shape for shape in shapes if shape != used],
        "keying": keying,
        # UX-192: the source kind, not the reading. The text renderer
        # built its keying sentence from `resolved_as` - always "url" -
        # so a pip resource said "any commit to this rebuilds all of
        # them", the sentence UX-181 shipped to remove from the table.
        "kind": kind,
        "direct_elements": sorted(direct),
        "direct_count": len(direct),
        "blast_elements": sorted(reachable),
        "blast_count": len(reachable),
        "building_count": building,
        "assembling_count": assembling,
        "by_element_kind": dict(sorted(by_kind.items(), key=lambda kv: (-kv[1], kv[0]))),
        "measured_us": sum(measured) if measured else None,
        "measured_elements": len(measured),
        "element_count": len(graph.elements),
        "has_inventory": bool(inventory),
        # UX-178: "this name is not an element here" and "this element
        # rebuilds nothing" are different answers.
        "element_exists": target in known,
        # UX-182: "not measured because you asked for the cheap answer"
        # is a different fact from "this run measured nothing".
        "measured": measure,
    }


def _by_depth(direct, reachable, successors, kinds, durations) -> List[dict]:
    """The closure as a hierarchy: `{element_uid, depth, element_kind,
    measured_us}`, direct consumers first.

    `UX-206` asked for the blast answer as an indented tree "over data
    `blast/v1` already carries". It did not carry it: the payload had
    two flat lists and no per-element depth, kind or cost at all. The
    viewer could only have got the shape by walking the graph in
    JavaScript, which is the second analysis the no-arithmetic rule
    exists to prevent - so the shape enters the JSON here, additively
    (`UX-190`: an addition does not bump the version).

    Breadth-first, so an element reachable by two paths is listed at the
    shorter one: the depth at which a reader first meets it, and the
    depth at which rebuilding it actually becomes unavoidable.
    """
    tree: List[dict] = []
    seen = set(direct)
    frontier = sorted(direct)
    depth = 0
    while frontier:
        for uid in frontier:
            tree.append({
                "element_uid": uid,
                "depth": depth,
                "element_kind": kinds.get(uid, "unknown"),
                "measured_us": durations.get(uid),
            })
        nxt = []
        for uid in frontier:
            for child in sorted(successors.get(uid) or ()):
                if child in seen or child not in reachable:
                    continue
                seen.add(child)
                nxt.append(child)
        frontier = nxt
        depth += 1
    return tree


def _tasks_of(run_dir: Path):
    """The run's normalized tasks, for the one duration definition.

    Goes through the analyzer rather than re-deriving durations from
    the trace, because `UX-53` is what happens when two places compute
    "how long did this element take" differently.
    """
    from .analyzer import BuildEfficiencyAnalyzer

    analyzer = BuildEfficiencyAnalyzer()
    # Not `section='graph'`: UX-47 lets the pipeline skip stages a
    # section does not consume, and normalization is one of them - which
    # on the first live run made every blast read "unmeasured" against a
    # run whose durations were right there.
    analyzer.analyze(run_dir)
    return getattr(analyzer, 'normalized_tasks', []) or []


# UX-178: the article follows pronunciation, not spelling - "an url" is
# how a vowel check reads it and not how anybody says it.
_ARTICLES = {"url": "a url", "path": "a path", "element": "an element"}


def _article(shape: str) -> str:
    return _ARTICLES.get(shape, f"a {shape}")


def format_blast_text(answer: dict) -> str:
    lines = [f"Blast radius: {answer['target']}"]
    lines.append(f"  Resolved as {_article(answer['resolved_as'])}"
                 + (f" (it also reads as {', '.join(_article(s) for s in answer['also_matched'])};"
                    f" resolution order is {', '.join(RESOLUTION_ORDER)})"
                    if answer['also_matched'] else ""))
    if not answer['direct_count']:
        lines.append("")
        if answer['resolved_as'] == 'element' and not answer['element_exists']:
            # UX-178: the sentence `classify_target`'s comment promised
            # and no code printed.
            lines.append("  No element of that name is in this run. Check the "
                         "spelling, or pass a path or a repository url.")
            return "\n".join(lines)
        if answer['resolved_as'] != 'element' and not answer['has_inventory']:
            lines.append("  Nothing matched, and this run carries no source "
                         "inventory - it was captured before `bga extract` wrote")
            lines.append("  one, so a url or a path cannot be resolved against it.")
        else:
            lines.append("  Nothing in this run sources it. Touching it rebuilds "
                         "nothing here.")
        return "\n".join(lines)

    named = ", ".join(answer['direct_elements'][:6])
    more = ("" if len(answer['direct_elements']) <= 6
            else f" (+{len(answer['direct_elements']) - 6} more)")
    lines += [
        "",
        f"  Sourced directly by {answer['direct_count']} element(s): {named}{more}",
        f"  Rebuilds {sources_mod.format_kind_split(answer['building_count'], answer['assembling_count'])}"
        f" of {answer['element_count']} in this build",
    ]
    if answer['by_element_kind']:
        lines.append("    " + ", ".join(f"{count} {kind}" for kind, count
                                        in answer['by_element_kind'].items()))
    if not answer.get('measured', True):
        lines.append("  Cost: not measured - re-run without --no-cost for the "
                     "measured rebuild time")
    elif answer['measured_us'] is None:
        lines.append("  Cost: unmeasured - no element of the blast ran in this build")
    else:
        lines.append(
            f"  Cost: {sources_mod.format_work(answer['measured_us'] / US_PER_S)} of build "
            f"work, measured for {answer['measured_elements']} of "
            f"{answer['blast_count']}")
    if answer['keying']:
        clause = sources_mod.keying_clause({'keying': answer['keying'],
                                            'kind': answer.get('kind')})
        lines.append(f"  {clause}")
    lines += [
        "",
        "  Work is the sum of those elements' own durations, not wall clock.",
    ]
    return "\n".join(lines)


def format_blast_json(answer: dict) -> str:
    return json.dumps(schemas.stamp(answer, schemas.BLAST), indent=2)
