"""`dev_close_task.py --check`'s newer properties, kept out of its body.

A module of its own so the size ledger (`UX-712`) holds for the tool it
serves: each function takes the paths it reads rather than importing
the tool, which imports this.
"""
import pathlib
import re
import sys

_FILE_ID = re.compile(r"^UX-0*(\d+)-")
_TITLE = re.compile(r"^# (.*)$", re.M)

#: `UX-937`: a §6 line opening with a path - its top-level directory, and
#: its first subdirectory when it has one.
_AREA_PATH = re.compile(r"^([a-z][a-z0-9_]*)/(?:([a-z][a-z0-9_]*)/)?", re.M)

#: `UX-688`: areas are code, not documents - the one top-level directory
#: §6 names that is not an area (`test_every_task_names_its_area.py`).
NOT_AN_AREA = frozenset({"docs"})


def unmerged_paths(ls_files):
    """The paths `git ls-files -u` holds at a merge stage, once each.

    `UX-935`: an unmerged path is listed once per stage, so every count
    read from `git ls-files` mid-merge is inflated by two per conflict.
    """
    return sorted({line.split("\t", 1)[1] for line in ls_files("-u")["all"]
                   if "\t" in line})


def index_is_merged(ls_files, real):
    """`True`, or exit 2 with one line naming a mid-merge index (`UX-935`).

    Only the real index is asked: a `--scenarios` sandbox reads no git.
    """
    unmerged = unmerged_paths(ls_files) if real else []
    if unmerged:
        print(f"refused: the git index is unmerged ({len(unmerged)} "
              f"path(s) mid-merge: {', '.join(unmerged)}) - stage the "
              f"resolution with `git add`, then derive; nothing was "
              f"checked or written", file=sys.stderr)
        raise SystemExit(2)
    return True


def declared_areas(guide: pathlib.Path, unknown):
    """`UX-937`: every top-level directory §6's tree names, with its first
    subdirectory - read from the tree, not an alternation typed here."""
    try:
        body = guide.read_text(encoding="utf-8")
    except OSError:
        return set()
    section = body.split("## 6.")[-1].split("\n## 7.")[0]
    found = {unknown}
    for top, sub in _AREA_PATH.findall(section):
        if top not in NOT_AN_AREA:
            found |= {top, f"{top}/{sub}"} if sub else {top}
    return found


def _shown(path, repo):
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def id_problems(scenarios: pathlib.Path, repo: pathlib.Path):
    """`UX-920`: an id that names two files, or a heading naming another id.

    Two branches filing under one id merge clean - two new files - and
    `task_file` then answers with the first, so the second is unreachable.
    """
    by_number, headings = {}, {}
    for path in sorted(scenarios.glob("UX-*.md")):
        match = _FILE_ID.match(path.name)
        if match:
            number = int(match.group(1))
            by_number.setdefault(number, []).append(path)
            title = _TITLE.search(path.read_text(encoding="utf-8"))
            said = re.match(r"UX-0*(\d+):", title.group(1)) if title else None
            headings[path] = (number, int(said.group(1)) if said else None)
    problems = [f"UX-{number} names {len(paths)} files: "
                + ", ".join(_shown(p, repo) for p in paths)
                for number, paths in sorted(by_number.items())
                if len(paths) > 1]
    for path, (number, said) in headings.items():
        if said is None:
            problems.append(f"{_shown(path, repo)}: no `# UX-NNN:` heading")
        elif said != number:
            other = ", ".join(_shown(p, repo) for p in by_number.get(said, []))
            problems.append(f"{_shown(path, repo)}: heading says UX-{said}, "
                            f"filename says UX-{number}"
                            + (f"; UX-{said} is {other}" if other else ""))
    return problems
