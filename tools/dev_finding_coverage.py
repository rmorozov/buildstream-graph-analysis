"""`UX-460`: which findings any committed capture actually produces.

`bga/findings.py`'s `FINDING_READERS` is the registry of what `analyze`
can conclude. Nothing read that registry against the fixtures, so a
heuristic could be added, wired, documented and shipped while no
committed capture ever reached it - every guard that touched it built
its own synthetic payload, and the suite stayed green.

**It reads what `analyze` emits.** The first cut of this census also
scanned the test sources for each quoted finding id and reported which
were "named by no test". It said `efficiency-score`,
`optimization-horizon` and `certified-headroom` had none; in snake_case
spellings they are in 7, 12 and 7 files. A text scan cannot tell a name
from a spelling of it - fixing guide §5, inside the census written to
find §5 gaps. So the only evidence this tool accepts is a finding id in
a real `analyze` payload.

`UX-449` is the same shape one level down (skip reasons, 25 undeclared
on a green tree) and `UX-376` is the rule it follows: a census names
what it could not assess.
"""
import argparse
import contextlib
import io
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from bga.findings import FINDING_READERS

#: Findings no committed capture can produce, and why. A declaration,
#: not an exemption: the reason is the reviewed part, and a finding
#: that is neither produced nor declared is what the guard fails on.
#:
#: Both of these need a build that did not finish, and every capture in
#: the tree is of one that did. Capturing a deliberately failing build
#: is a different fixture with a different contract (`UX-156` decides
#: what a failed build may verdict), not a row in this census.
UNREACHABLE = {
    "build-failed":
        "every committed capture is of a build that succeeded; this "
        "finding exists to describe one that did not (UX-156)",
    "failed-task-time":
        "same - it accounts for time spent in tasks that failed, and no "
        "committed capture has any",
}


def tracked_paths(root=REPO):
    """What `git ls-files` says this repository actually carries.

    Load-bearing, and it is the correction this tool was born from. The
    first cut globbed `examples/*/.bga/runs/*/run` and called what it
    found "committed captures". They are not committed and never have
    been: every `.bga` carries a `.gitignore` holding `*`, `UX-189`
    decided that a clone should not ship the capture archive, and
    `git ls-files 'examples/*/.bga'` returns **nothing**. The captures
    under `examples/` exist only on a machine that has built them.

    So the first census measured the working tree and reported it as the
    repository - fixing guide §5, in the census written to find §5 gaps,
    for the second time in two rounds. It said 7 findings were
    uncovered; on a clone the answer is 10.
    """
    import subprocess

    done = subprocess.run(["git", "ls-files"], cwd=str(root),
                          capture_output=True, text=True)
    return set(done.stdout.split())


def captures(root=REPO, tracked_only=True, also=()):
    """Run directories this repository carries, or all of them locally.

    `tracked_only` is the default because the question the guard asks -
    *can a finding be reached at all* - is about a clone. Pass `False`
    to see what this machine has in addition, which is what a
    contributor who has built the examples will find and a fresh
    checkout will not.

    `also` is run directories from outside the tree entirely, and it
    exists for `UX-473`: the two findings a curated capture cannot reach
    (`build-failed`, `failed-task-time`) need a build that *failed*, and
    the only thing that produces one is `tools/bga_gen_project.py` into
    a scratch directory. Nothing about such a run belongs in the
    repository (`UX-189`), so the census is told where it is rather than
    going looking.
    """
    found = set(root.glob("examples/*/.bga/runs/*/run"))
    found |= set(root.glob("tests/fixtures/*/run"))
    if tracked_only:
        tracked = tracked_paths(root)
        found = {run for run in found
                 if any(t.startswith(str(run.relative_to(root)))
                        for t in tracked)}
    return sorted(found) + [pathlib.Path(run).resolve() for run in also]


def label(run, root=REPO):
    """A short name for a capture: the project, not the timestamp.

    A run from `--also` is outside the tree and has no relative path, so
    it is named by the directory that holds it - which is the generated
    project's name, and the only part a reader of a job log needs."""
    try:
        rel = run.relative_to(root)
    except ValueError:
        parts = run.parts
        return parts[parts.index(".bga") - 1] if ".bga" in parts else run.name
    parts = rel.parts
    if ".bga" in parts:
        return parts[1] if parts[0] == "examples" else parts[0]
    return "/".join(parts[:-1])


def findings_of(run):
    """The finding ids one capture produces, or `None` if it will not
    analyse. In-process rather than a subprocess - the guard runs this
    over every capture in the tree and a fork each would be the whole
    cost of the file."""
    from bga.cli import main

    # Both streams: `analyze` narrates Plane 2's path on stderr, and a
    # census of every capture in the tree would print that line per
    # capture over the top of its own table.
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer), \
                contextlib.redirect_stderr(io.StringIO()):
            main(["analyze", str(run), "--format", "json"])
        return {f["id"] for f in json.loads(buffer.getvalue())["findings"]}
    except BaseException:
        return None


def coverage(root=REPO, tracked_only=True, also=()):
    """`{finding id: sorted [capture label]}` over the runs a clone has."""
    produced = {name: set() for name in FINDING_READERS}
    for run in captures(root, tracked_only, also):
        ids = findings_of(run)
        if ids is None:
            continue
        for name in ids & set(produced):
            produced[name].add(label(run, root))
    return {name: sorted(where) for name, where in produced.items()}


def uncovered(root=REPO, tracked_only=True, also=()):
    """The findings that are neither produced nor declared unreachable."""
    got = coverage(root, tracked_only, also)
    return sorted(name for name, where in got.items()
                  if not where and name not in UNREACHABLE)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quiet", action="store_true",
                        help="print only the findings nothing produces")
    parser.add_argument("--local", action="store_true",
                        help="count untracked captures under examples/ too - "
                             "what this machine has, not what a clone does")
    parser.add_argument("--also", action="append", default=[],
                        metavar="RUN",
                        help="a run directory outside the tree, repeatable - "
                             "for a generated project's capture (UX-473)")
    args = parser.parse_args(argv)

    got = coverage(tracked_only=not args.local, also=args.also)
    if not args.quiet:
        width = max(len(name) for name in got)
        for name in sorted(got):
            where = got[name]
            if where:
                shown = ", ".join(where)
            elif name in UNREACHABLE:
                shown = f"declared unreachable: {UNREACHABLE[name]}"
            else:
                shown = "*** NOTHING PRODUCES THIS ***"
            print(f"{name:{width}s}  {shown}")
        print()
    missing = uncovered(tracked_only=not args.local, also=args.also)
    scope = "this machine" if args.local else "a clone"
    if args.also:
        scope += f" + {len(args.also)} generated"
    print(f"({scope}) "
          f"{len(got)} findings | "
          f"{sum(1 for w in got.values() if w)} produced by a capture | "
          f"{len(UNREACHABLE)} declared unreachable | "
          f"{len(missing)} neither")
    for name in missing:
        print(f"  neither: {name}", file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
