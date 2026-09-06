#!/usr/bin/env python3
"""UX-685: a walk starts from a seed, not a memory.

Draws one scenario — an area (`UX-688`'s index), the `decompose`
skill's six input-class dimensions, and a reader role
(`docs/design/roles.md`) — all read from their own documents rather
than retyped here, so the vocabulary cannot drift from the thing it
names. Prints the scripted walk a `walk` subagent's driving half runs:
the capture recipe, the commands, the page controls to drive (the
census, `UX-665`), and the report shape it fills in.

The seed is the scenario's name: a SHA-256 digest of `seed:dimension`
picks each dimension's index, so the same seed reruns byte-identical
and every dimension draws independently of the others (not a shared
PRNG stream, which coupled role and population across seeds 1 and 2
in testing).

    python3 tools/dev_scenario.py --seed 1
"""
import argparse
import hashlib
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.dev_close_task import area_pages
from tools.dev_finding_coverage import tracked_paths

DECOMPOSE_SKILL = REPO / ".claude/skills/decompose/SKILL.md"
ROLES_DOC = REPO / "docs/design/roles.md"

_ROLE_ROW = re.compile(r"^\|\s*(R\d)\s*\|\s*(.+?)\s*\|")

#: One fragment of the scripted walk per class, keyed by the class's
#: leading word — the decompose table's own text, read rather than
#: retyped, so only the *mapping* is local and the vocabulary is not.
_RECIPE = {
    "population": {"0": "an empty run — zero built elements",
                  "1": "one element (`bga gen-synthetic --seed N --elements 1`)",
                  "many": "`examples/06-macro-micro-optimization` (9 elements)"},
    "contract version": {"legacy": "a committed legacy-contract fixture, read-only",
                         "current": "a fresh capture on today's schema"},
    "capture mode": {"cold": "a cold `bst build all.bst` (`XDG_CACHE_HOME` isolated)",
                     "incremental": "a second `bst build all.bst` in the same store"},
    "Plane 2": {"absent": "`bga snapshot -- bst build all.bst` — no hook, no spine",
               "hook only": "`bga snapshot -- bst build all.bst` — the LD_PRELOAD hook, no spine",
               "spine on": "`bga snapshot --trace-spine=on -- bst build all.bst`"},
    "reader": {"DOM shim": "the shim boot (`tests/dom_shim.mjs`), no browser",
              "real Chrome": "`tests/browser.py`'s `Browser(find_chrome())`",
              "the export": "the static export read as bytes, no boot"},
    "host": {"this machine": "run here",
             "CI only": "no local instrument — the `verify` skill's §7 pull"},
}


def _key(label):
    """The leading word of a class label, before its `,`/`(` detail."""
    return re.split(r"[,(]", label)[0].strip()


def partition_classes():
    """`{dimension: [class, ...]}`, read out of the `decompose` skill's
    own §2 partition table."""
    text = DECOMPOSE_SKILL.read_text(encoding="utf-8")
    section = text.split("## 2. Partition", 1)[1].split("\n## 3.", 1)[0]
    found = {}
    for line in section.splitlines():
        if not line.startswith("| ") or line.startswith("| dimension") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        found[cells[0]] = [c.strip() for c in cells[1].split("·")]
    return found


def roles():
    """`{Rn: description}`, read out of the role table's own two columns."""
    found = {}
    for line in ROLES_DOC.read_text(encoding="utf-8").splitlines():
        match = _ROLE_ROW.match(line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def _pick(seed, tag, options):
    """The option `seed:tag` names — a SHA-256 digest, not a shared
    PRNG stream, so each dimension draws independently of the others."""
    digest = hashlib.sha256(f"{seed}:{tag}".encode()).hexdigest()
    return options[int(digest, 16) % len(options)]


def draw(seed):
    """The scenario a seed names: one area, one role, one class per
    dimension — drawn in sorted-key order so the same seed reruns
    identically regardless of dict order."""
    areas = area_pages()
    if not areas:
        raise RuntimeError("the area index (UX-688) named no area")
    area = _pick(seed, "area", sorted(areas))
    role_map = roles()
    role = _pick(seed, "role", sorted(role_map))
    classes = partition_classes()
    chosen = {dim: _pick(seed, dim, classes[dim]) for dim in sorted(classes)}
    return {"seed": seed, "area": area, "area_size": len(areas[area]),
            "role": role, "role_text": role_map[role], "classes": chosen}


def describe(dim, label):
    return _RECIPE.get(dim, {}).get(_key(label), label)


def scripted_walk(seed):
    """The driving half's script, printed — nothing here executes it."""
    scenario = draw(seed)
    classes = scenario["classes"]
    lines = [f"scenario   seed={scenario['seed']}",
             f"area       {scenario['area']} ({scenario['area_size']} tasks)",
             f"role       {scenario['role']} — {scenario['role_text']}"]
    for dim in sorted(classes):
        lines.append(f"{dim:<17} {classes[dim]}")
    lines += ["", "capture recipe:",
             f"  {describe('population', classes['population'])}",
             f"  {describe('capture mode', classes['capture mode'])}",
             f"  {describe('Plane 2', classes['Plane 2'])}",
             f"  {describe('contract version', classes['contract version'])}",
             "commands:",
             "  bga analyze <run> --format json",
             "  bga correlate <run> --format json",
             "  bga view <run> --export export.html",
             "controls to drive (the census, UX-665):",
             "  python3 tools/dev_page_census.py export.html   "
             "# one instance per class it names",
             f"reader:    {describe('reader', classes['reader'])}",
             f"host:      {describe('host', classes['host'])}",
             "report shape: .claude/skills/walk/SKILL.md's ≤ 80-line "
             "template, plus `seed` and the answer-key rows it added"]
    return "\n".join(lines)


#: Four of the `walk` skill's fixed-shape report's own field labels,
#: aligned as the template has them (label, whitespace, content) — the
#: two-word compounds are what a round document's prose does not say
#: by coincidence at a line's start, unlike bare `capture`/`findings`.
_SHAPE = tuple(re.compile(rf"(?m)^{label}\s+\S")
              for label in ("answer key", "per plane", "findings", "friction"))
_SEED_LINE = re.compile(r"(?m)^seed\s")
_ROWS_LINE = re.compile(r"(?m)^rows added\s")


def is_walk_report(text):
    """Whether `text` follows the `walk` skill's own report shape."""
    return all(pattern.search(text) for pattern in _SHAPE)


def report_problems(documents):
    """`path: what is missing`, for every walk-shaped `(path, text)`
    lacking its seed or the answer-key rows it added (`UX-685`)."""
    problems = []
    for path, text in documents:
        if not is_walk_report(text):
            continue
        if not _SEED_LINE.search(text):
            problems.append(f"{path}: no seed line")
        if not _ROWS_LINE.search(text):
            problems.append(f"{path}: no answer-key rows added line")
    return problems


def audits_documents():
    """`(path, text)` for every tracked markdown file under `docs/audits/`.

    `tracked_paths` (`UX-687`) rather than a fresh `git ls-files` call —
    one subprocess call site for "what this repository actually
    carries", not a second one to drift from it.
    """
    return [(rel, (REPO / rel).read_text(encoding="utf-8"))
            for rel in sorted(tracked_paths())
            if rel.startswith("docs/audits/") and rel.endswith(".md")]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, required=True,
                        help="The scenario's name — reruns identically.")
    args = parser.parse_args(argv)
    print(scripted_walk(args.seed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
