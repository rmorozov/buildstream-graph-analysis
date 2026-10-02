"""UX-1289: `docs/README.md` is one screen of jobs, one link each, and holds no round log."""

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
INDEX = REPO / "docs/README.md"
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)\)")

#: The jobs the Required Fix names, by the page each row must open.
JOBS = {
    "try it": "../README.md",
    "optimise a real project": "guides/real-project.md",
    "run a pilot in CI": "guides/pilot.md",
    "share a capture": "guides/cli.md",
    "read the report": "guides/what-the-viewer-answers.md",
    "look up a command": "guides/cli.md",
    "look up a contract": "guides/json-contracts.md",
}

BUDGET = 80


def _rows():
    lines = INDEX.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("| I want to"))
    rows = []
    for line in lines[start + 2 :]:
        if not line.startswith("| "):
            break
        rows.append(line)
    return rows


def test_the_index_is_one_screen():
    lines = len(INDEX.read_text(encoding="utf-8").splitlines())
    assert lines <= BUDGET, f"docs/README.md is {lines} lines against UX-1289's {BUDGET}"


def test_the_index_links_no_round():
    rounds = [t for t in LINK.findall(INDEX.read_text(encoding="utf-8")) if re.search(r"round-\d+", t)]
    assert rounds == [], f"docs/README.md still links rounds - they live in docs/audits/README.md: {rounds}"


def test_every_job_is_one_row_with_one_link():
    rows = _rows()
    assert len(rows) >= len(JOBS), rows
    crowded = [row for row in rows if len(LINK.findall(row)) != 1]
    assert crowded == [], "a router row opens exactly one page:\n  " + "\n  ".join(crowded)
    missing = []
    for job, page in JOBS.items():
        row = next((r for r in rows if job.lower() in r.lower()), None)
        if row is None or LINK.findall(row)[0].split("#", 1)[0] != page:
            missing.append(f"{job!r} -> {page}")
    assert missing == [], "jobs with no row opening their page:\n  " + "\n  ".join(missing)
