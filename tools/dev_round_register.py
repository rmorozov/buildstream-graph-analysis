"""UX-744/772/782/926: which rounds happened, derived rather than typed.

    python tools/dev_round_register.py --check
    python tools/dev_round_register.py --write

Population is the committed union: every docs/audits/round-N.md, every
round the ledger's round column names (UX-782), and every round a task
file names - an Outcome's round marker or `Found by: round N` (UX-926).
Not `git log` - its reachability is a property of the clone (UX-776,
UX-781), so a round found only in a commit subject (`GIT_ONLY_ROUNDS`)
is accepted as lost, but checked against the tree: a git-only round
that gains a document, a ledger row or a task file reds `--check`.

A round's date is its own document's dateline (`document_date()`,
UX-772) - an empty cell, never a commit date, when it states none.
`first_commit_date()` is the independent check, and skips, naming the
depth, on a shallow clone.

`written_rounds()` holds back at most one round (`in_progress()`): the
newest number, when it has no document and is the one after the newest
document. A round in progress cannot commit the row that names it; a
claimed number past that is owed its document, not exempt (UX-926).
`--write` renders that view; `--check` reds when the file disagrees.
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
REGISTER = REPO / "docs/audits/round-register.md"
GIT = shutil.which("git") or "git"
sys.path.insert(0, str(REPO))

from tools import dev_close_task, dev_process_bands

#: `UX-772`: a heading's own parenthesised date, or the opening "Run on"
#: / "Opens at" sentence - a date elsewhere is a mention, not a claim.
DATELINE_RE = re.compile(
    r"^#\s.*\((20\d\d-\d\d-\d\d)\)"
    r"|^(?:Run on|Opens at)\b.*?\b(20\d\d-\d\d-\d\d)\b",
    re.MULTILINE)

ROUND_DOC_RE = re.compile(r"round-(\d+)\.md$")

#: `UX-782`: rounds only a commit subject names, measured once and
#: frozen, never re-derived. `UX-926` dropped the ten a task file names.
GIT_ONLY_ROUNDS = (31, 55, 60)

#: `UX-926`: `## Outcome (round N` or `**Round N`, read from the first
#: `## Outcome` on - a bold round above it is a mention.
OUTCOME_ROUND_RE = re.compile(
    r"^(?:## Outcome\b[^\n]*?\(round (\d+)\b|\*\*Round (\d+)\b)",
    re.MULTILINE)
FOUND_BY_ROUND_RE = re.compile(r"\*\*Found by:\*\*\s*round (\d+)\b",
                               re.IGNORECASE)


def task_file_rounds(scenarios=None):
    """Rounds the task files name, over `dev_close_task`'s population
    and its 8-line header bound, so `--scenarios` moves both."""
    scenarios = dev_close_task.SCENARIOS if scenarios is None else scenarios
    found = set()
    for path in pathlib.Path(scenarios).glob("UX-*.md"):
        if not dev_close_task._FILE_ID.match(path.name):
            continue
        text = path.read_text(encoding="utf-8")
        found.update(FOUND_BY_ROUND_RE.findall(
            "\n".join(text.splitlines()[:8])))
        _, heading, rest = text.partition("\n## Outcome")
        found.update(a or b for a, b in
                     OUTCOME_ROUND_RE.findall(heading.lstrip("\n") + rest))
    return {str(int(n)) for n in found}


def git_only_conflicts(documented=None, ledger_runs=None, named=None):
    """`[(round, where)]` for a `GIT_ONLY_ROUNDS` entry the tree now
    records - accepted-as-lost must stop being true loudly."""
    docs = documented_rounds() if documented is None else documented
    runs = (dev_process_bands.ledger_runs() if ledger_runs is None
            else ledger_runs)
    tasks = task_file_rounds() if named is None else named
    ledger_numbers = {run["round"] for run in runs}
    found = []
    for number in GIT_ONLY_ROUNDS:
        text = str(number)
        where = []
        if text in docs:
            where.append(f"docs/audits/round-{number}.md")
        if text in ledger_numbers:
            where.append("the ledger's round column")
        if text in tasks:
            where.append("a task file")
        if where:
            found.append((number, " and ".join(where)))
    return found


def _effective_git_only(documented=None, ledger_runs=None, named=None):
    conflicted = {n for n, _ in
                  git_only_conflicts(documented, ledger_runs, named)}
    return tuple(n for n in GIT_ONLY_ROUNDS if n not in conflicted)


def _git_only_note(effective):
    if not effective:
        return ("Every round once thought git-only now has a document, "
                "a ledger row or a task file naming it.")
    return (f"{len(effective)} round(s) ({min(effective)}-{max(effective)}) "
            "exist only as a commit subject - no document, no ledger row, "
            "no task file - and are accepted as lost, not re-derived from "
            "`git log`.")


def header(documented=None, ledger_runs=None):
    """The table's opening text, its git-only sentence net of conflicts."""
    effective = _effective_git_only(documented, ledger_runs)
    return (
        "# Round register\n\n"
        "Derived by `tools/dev_round_register.py --write` from the "
        "committed union: every docs/audits/round-N.md, every round "
        "the ledger's round column names, and every round a task file "
        "names in its Outcome or its `Found by` (UX-926) - never "
        "`git log`, whose reachability is a property of the clone "
        "(UX-782). "
        f"{_git_only_note(effective)} A round's date is its own "
        "document's dateline (UX-772); a round that states none is an "
        "empty cell, never a commit date. At most one round is held "
        "back as still in progress - the newest number, when it has no "
        "document and is the one after the newest document - and it "
        "is never written here. Never hand-edit; `--check` reds when "
        "this disagrees with the derivation.\n\n"
        "| round | date |\n|---|---|\n"
    )


#: `UX-776`: a shallow clone's `git log` stops early.
SHALLOW = ("{repo} is a shallow clone - `git log` cannot see the whole "
           "history first_commit_date() derives from, so its check "
           "means nothing here. `git fetch --unshallow` first (UX-776)")


def is_shallow(repo=None):
    """Whether `.git/shallow` names an ancestor of HEAD - a boundary this
    traversal passes through. Marker existence and missing parent
    objects were both proxies (`UX-781`)."""
    repo = str(repo or REPO)
    marker = pathlib.Path(repo) / ".git" / "shallow"
    if not marker.exists():
        return False
    for sha in marker.read_text(encoding="utf-8").split():
        cuts = subprocess.run([GIT, "merge-base", "--is-ancestor", sha,
                               "HEAD"], cwd=repo, capture_output=True,
                              check=False)
        if cuts.returncode == 0:
            return True
    return False


def shallow_depth(repo=None):
    """How many commits `.git/shallow` names - the skip's number."""
    repo = str(repo or REPO)
    marker = pathlib.Path(repo) / ".git" / "shallow"
    if not marker.exists():
        return 0
    return len(marker.read_text(encoding="utf-8").split())


def documented_rounds(repo=None):
    """Round numbers with a `docs/audits/round-N.md` file."""
    repo = repo or REPO
    return {m.group(1) for m in
            (ROUND_DOC_RE.search(p.name)
             for p in pathlib.Path(repo, "docs/audits").glob("round-*.md"))
            if m}


def _first_date_in_text(text):
    match = DATELINE_RE.search(text)
    if not match:
        return None
    return match.group(1) or match.group(2)


def document_date(number, repo=None):
    """The round's own dateline, or `None` - never a proxy for it."""
    repo = repo or REPO
    path = pathlib.Path(repo, "docs/audits", f"round-{number}.md")
    if not path.exists():
        return None
    return _first_date_in_text(path.read_text(encoding="utf-8"))


def first_commit_date(number, repo=None):
    """The date `docs/audits/round-N.md` was first added, from `git log`
    over its own path - independent of its text. `None` if never added."""
    repo = str(repo or REPO)
    path = f"docs/audits/round-{number}.md"
    out = subprocess.run(
        [GIT, "log", "--diff-filter=A", "--format=%ad", "--date=short",
         "--", path], cwd=repo, capture_output=True, text=True,
        check=True).stdout.strip().splitlines()
    return out[-1] if out else None


def rounds(documented=None, ledger_runs=None, dates=document_date,
           named=None):
    """`{round: {"date": str}}` over the committed union; a fixture hands
    in each source, and `dates`, without touching disk or git."""
    docs = documented_rounds() if documented is None else documented
    runs = (dev_process_bands.ledger_runs() if ledger_runs is None
            else ledger_runs)
    tasks = task_file_rounds() if named is None else named
    numbers = set(docs) | {run["round"] for run in runs} | set(tasks)
    return {number: {"date": dates(number) or ""} for number in numbers}


def _has_document(number, repo=REPO):
    return (repo / "docs/audits" / f"round-{number}.md").exists()


def in_progress(reg, is_documented):
    """The one round held back, or `None`: the newest number, undocumented
    and one past the newest document - a later claim is owed (UX-926)."""
    if not reg or is_documented(newest := max(reg, key=int)):
        return None
    documented = [int(n) for n in reg if is_documented(n)]
    if documented and int(newest) != max(documented) + 1:
        return None
    return newest


def written_rounds(reg=None, documented=None):
    """`rounds()` minus `in_progress()` (fixing-guide.md §7a)."""
    reg = rounds() if reg is None else reg
    is_documented = _has_document if documented is None else documented
    held = in_progress(reg, is_documented)
    return {number: row for number, row in reg.items() if number != held}


def render(reg):
    lines = [header().rstrip("\n")]
    for number in sorted(reg, key=int):
        lines.append(f"| {number} | {reg[number]['date']} |")
    return "\n".join(lines) + "\n"


def check():
    """`[]`, or each reason the file is not the derivation - a git-only
    conflict named before the generic disagreement."""
    if is_shallow():
        return [SHALLOW.format(repo=REPO)]
    problems = [
        f"round {number} is in GIT_ONLY_ROUNDS (accepted as lost) but "
        f"now exists at {where} - drop it from GIT_ONLY_ROUNDS"
        for number, where in git_only_conflicts()]
    want = render(written_rounds())
    if not REGISTER.exists():
        return [*problems, f"{REGISTER} does not exist - run --write"]
    have = REGISTER.read_text(encoding="utf-8")
    if have != want:
        problems.append(f"{REGISTER} disagrees with the derivation - "
                        "run --write")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if is_shallow():
        print(SHALLOW.format(repo=REPO), file=sys.stderr)
        return 1
    if args.write:
        REGISTER.write_text(render(written_rounds()), encoding="utf-8")
        print(f"wrote {REGISTER}")
        return 0
    if args.check:
        problems = check()
        for problem in problems:
            print(problem)
        return 1 if problems else 0
    print(render(written_rounds()), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
