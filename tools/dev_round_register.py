"""UX-744/772/782: which rounds happened, derived rather than typed.

    python tools/dev_round_register.py --check
    python tools/dev_round_register.py --write

Population is the committed union (UX-782): every docs/audits/round-N.md
plus every round the ledger's round column names. Not `git log` - its
reachability is a property of the clone (UX-776, UX-781), so a round
found only in a commit subject (`GIT_ONLY_ROUNDS`) is accepted as
lost, not chased into that instability - but checked against the tree:
a git-only round that gains a document or a ledger row reds `--check`
by name rather than leaving the header's count silently wrong.

A round's date is its own document's dateline (`document_date()`,
UX-772's "Run on"/"Opens at"/heading-parenthesised form) - an empty
cell, never `max(commit date)`, when the round states none. Comparing
the register's date to the dateline is tautological now they are the
same read; the surviving check reads `first_commit_date()` instead -
the commit that first added the document - and skips, naming the
depth, on a shallow clone rather than answering wrong.

`written_rounds()` excludes the newest round unless its own document
already exists: a round in progress cannot commit the row that names
it. `--write` renders that view; `--check` reds when the file
disagrees.
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

from tools import dev_process_bands

#: `UX-772`: a dateline, not any date - a heading's own parenthesised
#: date, or the opening sentence stating one ("Run on ...", "Opens at
#: `sha` (...)"). A date elsewhere in the text is a mention, not a claim
#: about when the round happened.
DATELINE_RE = re.compile(
    r"^#\s.*\((20\d\d-\d\d-\d\d)\)"
    r"|^(?:Run on|Opens at)\b.*?\b(20\d\d-\d\d-\d\d)\b",
    re.MULTILINE)

ROUND_DOC_RE = re.compile(r"round-(\d+)\.md$")

#: `UX-782`: rounds that exist only as a commit subject - no document,
#: no ledger row - measured once against this branch's `git log`
#: (Motivation) and frozen: a later clone seeing a different set is
#: exactly the instability this row stops the register from reading.
#: Accepted as lost rather than chased; never re-derived.
GIT_ONLY_ROUNDS = (26, 29, 31, 47, 48, 50, 52, 53, 55, 58, 60, 67, 69)


def git_only_conflicts(documented=None, ledger_runs=None):
    """`[(round, where)]` for a `GIT_ONLY_ROUNDS` entry that has since
    gained a document or a ledger row - accepted-as-lost is a claim
    about the tree, not a permanent fact, and the sentence that states
    it must stop being true silently. `where` names the place, so
    `check()` can point at it rather than just at a stale count."""
    docs = documented_rounds() if documented is None else documented
    runs = (dev_process_bands.ledger_runs() if ledger_runs is None
            else ledger_runs)
    ledger_numbers = {run["round"] for run in runs}
    found = []
    for number in GIT_ONLY_ROUNDS:
        text = str(number)
        where = []
        if text in docs:
            where.append(f"docs/audits/round-{number}.md")
        if text in ledger_numbers:
            where.append("the ledger's round column")
        if where:
            found.append((number, " and ".join(where)))
    return found


def _effective_git_only(documented=None, ledger_runs=None):
    conflicted = {n for n, _ in git_only_conflicts(documented, ledger_runs)}
    return tuple(n for n in GIT_ONLY_ROUNDS if n not in conflicted)


def _git_only_note(effective):
    if not effective:
        return ("Every round once thought git-only now has a document "
                "or a ledger row.")
    return (f"{len(effective)} round(s) "
            f"({min(effective)}-{max(effective)}) exist only "
            "as a commit subject - no document, no ledger row - and are "
            "accepted as lost, not re-derived from `git log`.")


def header(documented=None, ledger_runs=None):
    """The table's opening text - the git-only sentence derived from
    `GIT_ONLY_ROUNDS` minus whichever entries `git_only_conflicts()`
    has just found in the tree, so the sentence is never stale while
    `check()` is also naming the conflict as a problem."""
    effective = _effective_git_only(documented, ledger_runs)
    return (
        "# Round register\n\n"
        "Derived by `tools/dev_round_register.py --write` from the "
        "committed union: every docs/audits/round-N.md plus every round "
        "the ledger's round column names - never `git log`, whose "
        "reachability is a property of the clone (UX-782). "
        f"{_git_only_note(effective)} A round's date is its own "
        "document's dateline (UX-772); a round that states none is an "
        "empty cell, never a commit date. A round still in progress - "
        "the newest number, unless its own document already exists - "
        "is never written here. Never hand-edit; `--check` reds when "
        "this disagrees with the derivation.\n\n"
        "| round | date |\n|---|---|\n"
    )


#: `UX-776`: a shallow clone's `git log` stops early, so `is_shallow()`
#: and `first_commit_date()` are a property of the checkout even
#: though the population and the dateline no longer are.
SHALLOW = ("{repo} is a shallow clone - `git log` cannot see the whole "
           "history first_commit_date() derives from, so its check "
           "means nothing here. `git fetch --unshallow` first (UX-776)")


def is_shallow(repo=None):
    """Whether `git log` stops at a boundary inside HEAD's own history:
    `.git/shallow` names a commit that is an ancestor of HEAD.

    Three readings were tried and two were proxies. The marker's
    existence is one (a stale marker cuts nothing). Whether the
    boundary's parent *object* is absent is the other, and `UX-781`
    falsified it: `git fetch --depth=200` on a complete clone cut 1,541
    commits to 855 while every parent object stayed on disk, so that
    test read False on a repository git was already refusing to walk.
    A commit in `.git/shallow` is parentless to every traversal
    whatever objects exist - so the question is only whether the
    traversal this derivation runs passes through one.
    """
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
    """How many commits `.git/shallow` names as the boundary - the
    number a shallow-clone skip states. Reads the same marker
    `is_shallow()` does rather than spending a second `git` call."""
    repo = str(repo or REPO)
    marker = pathlib.Path(repo) / ".git" / "shallow"
    if not marker.exists():
        return 0
    return len(marker.read_text(encoding="utf-8").split())


def documented_rounds(repo=None):
    """Round numbers with a `docs/audits/round-N.md` file - one half
    of the committed union (UX-782); the ledger's round column is the
    other."""
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
    """The round's own dateline, or `None` if its document states
    none - never a proxy (a file's first-commit date, or any other
    date the text happens to mention) for a claim it never made."""
    repo = repo or REPO
    path = pathlib.Path(repo, "docs/audits", f"round-{number}.md")
    if not path.exists():
        return None
    return _first_date_in_text(path.read_text(encoding="utf-8"))


def first_commit_date(number, repo=None):
    """The date `docs/audits/round-N.md` was first added, read from
    `git log` over the file's own path - independent of the document's
    text, which the register's date now equals by construction
    (`document_date()`). `None` if the path was never added on this
    history."""
    repo = str(repo or REPO)
    path = f"docs/audits/round-{number}.md"
    out = subprocess.run(
        [GIT, "log", "--diff-filter=A", "--format=%ad", "--date=short",
         "--", path], cwd=repo, capture_output=True, text=True,
        check=True).stdout.strip().splitlines()
    return out[-1] if out else None


def rounds(documented=None, ledger_runs=None, dates=document_date):
    """`{round: {"date": str}}` - the committed union (UX-782): every
    round with a document, or a row in the ledger. `dates` reads each
    round's own dateline by default; a fixture hands this its own
    population and date source without touching disk or git."""
    docs = documented_rounds() if documented is None else documented
    runs = (dev_process_bands.ledger_runs() if ledger_runs is None
            else ledger_runs)
    numbers = set(docs) | {run["round"] for run in runs}
    return {number: {"date": dates(number) or ""} for number in numbers}


def _has_document(number, repo=REPO):
    return (repo / "docs/audits" / f"round-{number}.md").exists()


def written_rounds(reg=None, documented=None):
    """`rounds()` minus a round still in progress: the newest number,
    unless its own document already exists - the self-reference fix
    (fixing-guide.md §7a), bounded so it cannot hold a finished round
    back forever waiting for a strictly higher one."""
    reg = rounds() if reg is None else reg
    if not reg:
        return {}
    is_documented = _has_document if documented is None else documented
    newest = max(reg, key=int)
    if is_documented(newest):
        return dict(reg)
    return {number: row for number, row in reg.items() if number != newest}


def render(reg):
    lines = [header().rstrip("\n")]
    for number in sorted(reg, key=int):
        lines.append(f"| {number} | {reg[number]['date']} |")
    return "\n".join(lines) + "\n"


def check():
    """`[]` when the file on disk matches `written_rounds()` and every
    `GIT_ONLY_ROUNDS` entry is still absent from the tree, else the
    reason(s) it is not - a conflict named by round and where before
    the generic disagreement, so `--write` is not the only answer
    offered for "drop it from `GIT_ONLY_ROUNDS`"."""
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
