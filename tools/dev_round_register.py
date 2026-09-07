"""UX-744: which rounds happened, derived rather than typed.

    python tools/dev_round_register.py --check
    python tools/dev_round_register.py --write

A round exists if a commit's subject names it or the ledger prices it
(`commit_signal()`, `ledger_runs()`); its date is the latest such
commit's date. No ids-closed column is derived here: a verifier found
`commit_signal()` cannot tell a commit that *documents* an earlier
round from one that is *in* it - a retroactive documentation commit
legitimately names the round it describes, dragging that round's date
to its own. `document_date()` reads a round's own **dateline** -
a heading's parenthesised date, or an opening "Run on"/"Opens at"
sentence - never a document's first date of any kind (`UX-772`):
rounds 76 and 85 each carry an earlier, incidental date that is not
their own, and a document stating none reads `None`.

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
#: `UX-772`: a dateline, not any date - a heading's own parenthesised
#: date, or the opening sentence stating one ("Run on ...", "Opens at
#: `sha` (...)"). A date elsewhere in the text is a mention, not a claim
#: about when the round happened.
DATELINE_RE = re.compile(
    r"^#\s.*\((20\d\d-\d\d-\d\d)\)"
    r"|^(?:Run on|Opens at)\b.*?\b(20\d\d-\d\d-\d\d)\b",
    re.MULTILINE)

HEADER = (
    "# Round register\n\n"
    "Derived by `tools/dev_round_register.py --write` from the commits "
    "naming a round and the ledger's round column. A round still in "
    "progress - the newest number, unless its own document already "
    "exists - is never written here. Never hand-edit; `--check` reds "
    "when this disagrees with the derivation.\n\n"
    "| round | date |\n|---|---|\n"
)


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
    match = DATELINE_RE.search(text)
    if not match:
        return None
    return match.group(1) or match.group(2)


def document_date(number, repo=REPO):
    """The round's own dateline, or `None` if its document states
    none - never a proxy (a file's first-commit date, or any other
    date the text happens to mention) for a claim it never made."""
    path = repo / "docs/audits" / f"round-{number}.md"
    if not path.exists():
        return None
    return _first_date_in_text(path.read_text(encoding="utf-8"))


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
