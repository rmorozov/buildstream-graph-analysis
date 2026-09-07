"""`UX-744`: which rounds happened, derived rather than typed.

    python tools/dev_round_register.py --check
    python tools/dev_round_register.py --write

Three sources, none authoritative alone: `closed.md`'s rows (what is
actually closed), the commit whose subject names a round (`\\bround
\\d+\\b`, its date, the ids its message mentions), and
`dev_process_bands.py`'s ledger round column. A round exists if a
commit names it or the ledger prices it; its "ids closed" are the ids
its commits mention that `closed.md` also shows closed - a filed-not-
closed id (`UX-707` in round 94's subject) is dropped by that join.
`--write` renders `docs/audits/round-register.md`; `--check` reds when
the file on disk disagrees with the derivation, `dev_close_task.py
--check`'s pattern for a table that must never be hand-edited.
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
CLOSED = REPO / "docs/backlog/scenarios/closed.md"
REGISTER = REPO / "docs/audits/round-register.md"
GIT = shutil.which("git") or "git"
sys.path.insert(0, str(REPO))

from tools import dev_process_bands

ROUND_RE = re.compile(r"\bround\s+(\d+)\b", re.IGNORECASE)
CLOSED_ROW_RE = re.compile(r"^\|\s*(UX-\d+)\s*\|", re.MULTILINE)
RANGE_RE = re.compile(r"UX-(\d+)\.\.(?:UX-)?(\d+)")
LIST_RE = re.compile(r"UX-(\d+)((?:\s*,\s*\d+)+)")
SINGLE_RE = re.compile(r"UX-(\d+)")

HEADER = ("# Round register\n\n"
          "Derived by `tools/dev_round_register.py --write` from "
          "`closed.md`, the commits naming a round, and the ledger's "
          "round column (`UX-744`). Never hand-edit; `--check` reds "
          "when this disagrees with the derivation.\n\n"
          "| round | date | ids closed |\n|---|---|---|\n")


def closed_ids():
    """Every id `closed.md` actually shows closed."""
    return frozenset(CLOSED_ROW_RE.findall(CLOSED.read_text(encoding="utf-8")))


def _ids_in(text):
    """Range, comma-list, then bare `UX-N` mentions - `UX-651, 652, 655,
    657` (round 89's commit) is four ids, not a 651..657 range."""
    ids, spans = set(), []
    for m in RANGE_RE.finditer(text):
        lo, hi = sorted((int(m.group(1)), int(m.group(2))))
        ids.update(str(n) for n in range(lo, hi + 1))
        spans.append(m.span())
    for m in LIST_RE.finditer(text):
        ids.add(m.group(1))
        ids.update(re.findall(r"\d+", m.group(2)))
        spans.append(m.span())
    masked = list(text)
    for start, end in spans:
        masked[start:end] = " " * (end - start)
    for m in SINGLE_RE.finditer("".join(masked)):
        ids.add(m.group(1))
    return ids


def _commits():
    out = subprocess.run(
        [GIT, "log", "--format=%H%x1f%ad%x1f%B%x1e", "--date=short"],
        cwd=str(REPO), capture_output=True, text=True, check=True).stdout
    for entry in out.split("\x1e"):
        if not entry.strip():
            continue
        _sha, date, body = entry.strip("\n").split("\x1f", 2)
        yield date, body


def commit_signal():
    """`{round: {"dates": [...], "ids": set(...)}}` from the commits
    alone, unfiltered by `closed.md` - independent of `rounds()`'s own
    result, so a "-" ids row can be checked against it rather than
    against itself."""
    by_round = {}
    for date, body in _commits():
        subject = body.splitlines()[0] if body else ""
        match = ROUND_RE.search(subject)
        if not match:
            continue
        number = match.group(1)
        entry = by_round.setdefault(number, {"dates": [], "ids": set()})
        entry["dates"].append(date)
        entry["ids"].update(f"UX-{n}" for n in _ids_in(body))
    return by_round


def ids_are_mentioned(number):
    """Whether `commit_signal()` currently holds an id for `number`.
    Reads the same scan `rounds()` does, so this catches ids dropped
    after the scan, never a bug inside `commit_signal()` itself - a
    corrupted scan reads as "nothing was ever mentioned" here too.
    `tests/unit/test_a_run_is_priced.py`'s `DASH_ROUNDS` pin is what
    catches that layer."""
    return bool(commit_signal().get(number, {}).get("ids"))


def rounds():
    """`{round: {"date": str, "ids": sorted[str]}}`, every round any
    source shows happened."""
    closed = closed_ids()
    by_round = commit_signal()
    for run in dev_process_bands.ledger_runs():
        by_round.setdefault(run["round"], {"dates": [], "ids": set()})
    result = {}
    for number, entry in by_round.items():
        ids = sorted(entry["ids"] & closed, key=lambda i: int(i.split("-")[1]))
        date = max(entry["dates"]) if entry["dates"] else "—"
        result[number] = {"date": date, "ids": ids}
    return result


def render(reg):
    lines = [HEADER.rstrip("\n")]
    for number in sorted(reg, key=int):
        ids = ", ".join(reg[number]["ids"]) or "—"
        lines.append(f"| {number} | {reg[number]['date']} | {ids} |")
    return "\n".join(lines) + "\n"


def check():
    """`[]` when the file on disk matches the derivation, else the
    one-line reason it does not."""
    want = render(rounds())
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
        REGISTER.write_text(render(rounds()), encoding="utf-8")
        print(f"wrote {REGISTER}")
        return 0
    if args.check:
        problems = check()
        for problem in problems:
            print(problem)
        return 1 if problems else 0
    print(render(rounds()), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
