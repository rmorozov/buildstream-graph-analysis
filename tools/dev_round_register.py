"""UX-744: which rounds happened, derived rather than typed.

    python tools/dev_round_register.py --check
    python tools/dev_round_register.py --write

A round exists if a commit's subject names it or the ledger prices it
(`commit_signal()`, `ledger_runs()`); its date is the latest such
commit's date. No ids-closed column is derived here: a verifier found
`commit_signal()` cannot tell a commit that *documents* an earlier
round from one that is *in* it - a retroactive documentation commit
legitimately names the round it describes, dragging that round's date
to its own. `document_date()` reads a round's own document instead,
for the comparison test that catches exactly that.

`written_rounds()` excludes the newest round unless its own document
already exists: a round in progress cannot commit the row that names
it, but holding a *documented* round back forever, waiting for a
strictly higher round to appear, is the silence this row exists to
close (fixing-guide.md §7a). `--write` renders that view; `--check`
reds when the file disagrees. Every scanning function takes its
source as an optional argument so a fixture can drive it without
touching real git history.
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

ROUND_RE = re.compile(r"\bround\s+(\d+)\b", re.IGNORECASE)
DATE_RE = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")

HEADER = (
    "# Round register\n\n"
    "Derived by `tools/dev_round_register.py --write` from the commits "
    "naming a round and the ledger's round column. A round still in "
    "progress - the newest number, unless its own document already "
    "exists - is never written here. Never hand-edit; `--check` reds "
    "when this disagrees with the derivation.\n\n"
    "| round | date |\n|---|---|\n"
)


#: `UX-776`: a shallow clone's `git log` stops early, so this
#: derivation is a property of the checkout. 610 commits derived 32
#: rounds here; CI's 1,538 derived 71.
SHALLOW = ("{repo} is a shallow clone - `git log` cannot see the whole "
           "history this derives from, so neither --check nor --write "
           "means anything here. `git fetch --unshallow` first (UX-776)")


def is_shallow(repo=None):
    """Whether `git log` is actually cut: a commit `.git/shallow` names
    has a parent whose object is absent.

    Neither the marker's existence nor `rev-parse --is-shallow-
    repository` (which reads it) answers this - a runner holding all
    1,538 commits carried a stale marker, and the first version of this
    reddened CI on it. A grafted boundary still records its parent in
    its own object; what it lacks is the parent.
    """
    repo = str(repo or REPO)
    marker = pathlib.Path(repo) / ".git" / "shallow"
    if not marker.exists():
        return False
    for sha in marker.read_text(encoding="utf-8").split():
        body = subprocess.run([GIT, "cat-file", "-p", sha], cwd=repo,
                              capture_output=True, text=True, check=False)
        if body.returncode != 0:
            continue
        for line in body.stdout.splitlines():
            if not line.startswith("parent "):
                continue
            here = subprocess.run([GIT, "cat-file", "-e", line.split()[1]],
                                  cwd=repo, capture_output=True, check=False)
            if here.returncode != 0:
                return True
    return False


def _commits(repo=REPO):
    """`(date, body)` per real commit, oldest git provides - the
    production source; a fixture hands `commit_signal` its own list."""
    out = subprocess.run(
        [GIT, "log", "--format=%H%x1f%ad%x1f%B%x1e", "--date=short"],
        cwd=str(repo), capture_output=True, text=True, check=True).stdout
    for entry in out.split("\x1e"):
        if not entry.strip():
            continue
        _sha, date, body = entry.strip("\n").split("\x1f", 2)
        yield date, body


def commit_signal(commits=None):
    """`{round: {"dates": [...]}}` - subject-matched only, so a body
    naming an old round in passing is not counted."""
    by_round = {}
    for date, body in (commits if commits is not None else _commits()):
        subject = body.splitlines()[0] if body else ""
        match = ROUND_RE.search(subject)
        if not match:
            continue
        number = match.group(1)
        by_round.setdefault(number, {"dates": []})["dates"].append(date)
    return by_round


def rounds(commits=None, ledger_runs=None):
    """`{round: {"date": str}}` - every round a commit subject or the
    ledger shows happened, the newest included."""
    by_round = commit_signal(commits)
    runs = (dev_process_bands.ledger_runs() if ledger_runs is None
            else ledger_runs)
    for run in runs:
        by_round.setdefault(run["round"], {"dates": []})
    return {number: {"date": max(entry["dates"]) if entry["dates"] else "—"}
            for number, entry in by_round.items()}


def _first_date_in_text(text):
    match = DATE_RE.search(text)
    return match.group(1) if match else None


def _first_commit_date(path, repo=REPO):
    """The date `path` was first added - a round written
    contemporaneously (no dateline in its own text) still has one."""
    out = subprocess.run(
        [GIT, "log", "--format=%ad", "--date=short", "--follow",
         "--diff-filter=A", "--", str(path)],
        cwd=str(repo), capture_output=True, text=True, check=True).stdout
    lines = [line for line in out.splitlines() if line.strip()]
    return lines[-1] if lines else None


def document_date(number, repo=REPO):
    """The round's own document's date - the first date its text
    states, or the file's own first-commit date if it states none."""
    path = repo / "docs/audits" / f"round-{number}.md"
    if not path.exists():
        return None
    return (_first_date_in_text(path.read_text(encoding="utf-8"))
            or _first_commit_date(path, repo))


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
    lines = [HEADER.rstrip("\n")]
    for number in sorted(reg, key=int):
        lines.append(f"| {number} | {reg[number]['date']} |")
    return "\n".join(lines) + "\n"


def check():
    """`[]` when the file on disk matches `written_rounds()`, else the
    one-line reason it does not."""
    if is_shallow():
        return [SHALLOW.format(repo=REPO)]
    want = render(written_rounds())
    if not REGISTER.exists():
        return [f"{REGISTER} does not exist - run --write"]
    have = REGISTER.read_text(encoding="utf-8")
    if have != want:
        return [f"{REGISTER} disagrees with the derivation - run --write"]
    return []


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
