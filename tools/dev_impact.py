#!/usr/bin/env python3
"""UX-687: what a change reaches, derived instead of grepped five times.

`dev_touching` answers *which guards run*. This answers the design-stage
question one step earlier: which **contracts** a module emits, which
**findings** it produces, which **guides** name it or its command, which
**styleguide** sections a viewer module cites, and which **open filings**
sit on the same topic.

Each row has one source and no second copy:

```text
contracts   bga.contracts.inventory()      contract id -> emitting module
findings    bga.findings.FINDING_READERS   id mentioned in the module
guides      docs/guides/**, README.md      the module or its `bga` command
styleguide  the viewer module's own text   the sections it cites
guards      dev_touching.select()          grep u map u census
filings     the open index                 same Topic (Area: UX-688)
```

The tool lists; the session judges what a change may break.
"""
import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import dev_touching

from bga import contracts, findings

#: Where a reader meets a module by name, or by the command it serves.
PROSE = ("docs/guides", "README.md")
INDEX = REPO / "docs/backlog/scenarios/README.md"
STYLEGUIDE_SECTION = re.compile(r"§\s?[0-9]+[a-z]?(?:\.[0-9]+)?")


def modules(target, stream=None):
    """The module paths a target names: `-`, a `UX-NNN`, or a path.

    `-` reads paths on stdin, so a diff arrives as
    `git diff --name-only | dev_impact.py -`. The tool shells out to
    nothing: the caller owns which revisions it is comparing, and this
    stays a reader.
    """
    if target in (None, "", "-"):
        names = (stream or sys.stdin).read().split()
    elif re.fullmatch(r"UX-[0-9]+", target or ""):
        hits = list((REPO / "docs/backlog/scenarios").glob(
            f"UX-0*{target.split('-')[1]}-*.md"))
        text = hits[0].read_text(encoding="utf-8") if hits else ""
        names = re.findall(r"`((?:bga|tools)/[A-Za-z0-9_/]+\.py)`", text)
    else:
        names = [target]
    return sorted({n for n in dict.fromkeys(names)
                   if n.startswith(("bga/", "tools/"))})


def contracts_of(module):
    """Contract ids this module emits, joined by name.

    Three sources were tried and two answer a different question.
    `inventory()` gives where the `SCHEMA` constant is *declared* -
    `bga.schemas` for 24 of 25 ids. The module's own text does not
    name its id at all (`correlate.py` never says `correlate/v2`).
    What is left is the name: the id's stem against the module's stem
    or the `bga` command it serves, which places **14 of 25**. The
    rest are named by `unplaced()` rather than dropped, because a row
    that is silently partial is worse than one that says so.
    """
    stem = pathlib.Path(module).stem
    names = {stem, command_of(module) or stem}
    return sorted(cid for cid in contracts.inventory()
                  if cid.split("/")[0].replace("-", "_") in names
                  or cid.split("/")[0].split("-")[0] in names)


def unplaced():
    """Contract ids no module claims, by the same rule that places them.

    Derived from `contracts_of` rather than restating its join: the
    first cut had a second copy of the rule and the two disagreed on
    `analyze/*`, whose command is `analyze` and whose module is
    `analyzer.py`.
    """
    placed = set()
    for module in sorted((REPO / "bga").rglob("*.py")):
        placed |= set(contracts_of(str(module.relative_to(REPO))))
    return sorted(set(contracts.inventory()) - placed)


def findings_of(module):
    """Finding ids this module names - `findings.py` is the registry."""
    if module.endswith("bga/findings.py"):
        return []
    try:
        text = (REPO / module).read_text(encoding="utf-8")
    except OSError:
        return []
    return sorted(i for i in findings.FINDING_READERS
                  if re.search(rf"\b{re.escape(i)}\b", text))


def command_of(module):
    """The `bga` subcommand a module serves, by name, or `None`."""
    stem = pathlib.Path(module).stem
    return stem if stem in _subcommands() else None


def _subcommands():
    text = (REPO / "bga/cli.py").read_text(encoding="utf-8")
    return set(re.findall(r"add_parser\(\s*[\"']([a-z-]+)[\"']", text))


def prose_of(module):
    """`path:line` where a guide or the README names it or its command."""
    needles = [pathlib.Path(module).stem]
    command = command_of(module)
    if command:
        needles.append(f"bga {command}")
    rows = []
    for root in PROSE:
        base = REPO / root
        files = [base] if base.is_file() else sorted(base.rglob("*.md"))
        for doc in files:
            for n, line in enumerate(
                    doc.read_text(encoding="utf-8").splitlines(), 1):
                if any(needle in line for needle in needles):
                    rows.append(f"{doc.relative_to(REPO)}:{n}")
    return rows


def styleguide_of(module):
    """The styleguide sections a viewer module cites, in its own text."""
    js = REPO / module
    if not module.startswith("bga/viewer/") or not js.exists():
        return []
    return sorted(set(STYLEGUIDE_SECTION.findall(
        js.read_text(encoding="utf-8"))))


def filings_of(module):
    """Open rows on the module's topic. `UX-688` will make this an area."""
    topic = _topic_of(module)
    if not topic:
        return []
    rows = []
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 4 and cells[1].startswith("UX-") and cells[3] == topic:
            rows.append(f"{cells[1]} {cells[2].split(']')[0].lstrip('[')}")
    return rows


def _topic_of(module):
    """The index topic a module's guards sit under, by its own path."""
    if module.startswith("bga/viewer/"):
        return "viewer"
    if module.startswith("tools/"):
        return "guards"
    return {"cli.py": "cli", "store.py": "store"}.get(
        pathlib.Path(module).name, "analysis")


#: A diff touching one of these is a design question as well as a
#: code one, so `self-review` sends it on. Each is a surface whose
#: reader is not the diff's author: a published key, the ground-truth
#: spec, a hook every session runs, a skill every round reads.
DESIGN_SURFACES = (
    ("a contract", lambda p: p == "bga/schemas.py"),
    ("the spec", lambda p: p.startswith("docs/spec/")),
    ("a hook", lambda p: p.startswith(".claude/hooks/")),
    ("a skill", lambda p: p.startswith(".claude/skills/")),
)


def route(paths):
    """`(destination, reasons)` for a diff - `UX-701`'s routing rule.

    `design-review` when the diff reaches a surface whose reader is
    somebody other than its author, `self-review` otherwise. The rule
    is here rather than in the skill's prose so a guard can run it.
    """
    reasons = sorted({name for name, matches in DESIGN_SURFACES
                      for path in paths if matches(path)})
    return ("design-review" if reasons else "self-review"), reasons


def report(module):
    """Every row for one module, each from the source named above."""
    guards, _ = dev_touching.select([module])
    return {
        "contracts": contracts_of(module),
        "findings": findings_of(module),
        "guides": prose_of(module),
        "styleguide": styleguide_of(module),
        "guards": sorted(guards),
        "filings": filings_of(module),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("target", nargs="?", default="-",
                        help="`-` for paths on stdin, a UX-NNN, or a module")
    parser.add_argument("--route", action="store_true",
                        help="print where UX-701's rule sends this diff")
    parser.add_argument("--rows", type=int, default=8,
                        help="how many entries to print per row")
    args = parser.parse_args(argv)

    if args.route:
        paths = (sys.stdin.read().split() if args.target in (None, "", "-")
                 else [args.target])
        where, why = route(paths)
        print(f"{where}" + (f"  ({', '.join(why)})" if why else ""))
        return 0

    left = unplaced()
    if left:
        print(f"{len(left)} contract id(s) no module name claims: "
              f"{', '.join(left)}\n")
    found = modules(args.target)
    if not found:
        print(f"no bga/ or tools/ module in {args.target!r}")
        return 0
    for module in found:
        print(module)
        for name, values in report(module).items():
            if not values:
                continue
            head = values[:args.rows]
            more = f"  (+{len(values) - len(head)})" if len(
                values) > len(head) else ""
            print(f"  {name:<11} {len(values):>3}  "
                  f"{', '.join(head)}{more}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
