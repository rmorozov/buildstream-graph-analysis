"""UX-696: a commit body is eight lines, and CI reads the ones a branch adds.

    python3 tools/dev_commit_bodies.py [BASE]        # default origin/main

`CLAUDE.md`'s register states the budget and nothing read it. Measured
on the branch that added this guard: eleven of its commits were over,
the worst at fifteen lines, several of them written while the session
was arguing for terseness. The task file is the record; the body says
what changed and points at it.

The footer lines the harness appends (`Co-Authored-By:`,
`Claude-Session:`) do not count, and neither do blank lines.

Commits authored before `RULE_FROM` are grandfathered. A date rather
than a list of hashes: author dates survive a rebase, and a hash list
would go stale the first time this branch is merged.
"""
import re
import subprocess
import sys

CAP = 8
RULE_FROM = "2026-09-06T21:52:00+00:00"
FOOTER = re.compile(r"^(Co-Authored-By|Claude-Session|Signed-off-by|"
                    r"Co-authored-by):", re.I)


def body_lines(body):
    """The lines a body spends, footer and blanks excluded."""
    return [line for line in body.splitlines()
            if line.strip() and not FOOTER.match(line.strip())]


def over_cap(base="origin/main", cap=CAP, since=RULE_FROM):
    """`(sha, subject, n)` for each commit the branch adds that is over."""
    out = subprocess.run(
        ["git", "log", f"{base}..HEAD", "--no-merges",
         f"--since={since}", "--format=%H%x1f%s%x1f%b%x1e"],
        capture_output=True, text=True, check=True).stdout
    over = []
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if not record:
            continue
        sha, subject, body = record.split("\x1f", 2)
        n = len(body_lines(body))
        if n > cap:
            over.append((sha[:9], subject, n))
    return over


def main(argv):
    base = argv[1] if len(argv) > 1 else "origin/main"
    over = over_cap(base)
    if not over:
        print(f"every commit {base}..HEAD is within {CAP} body lines")
        return 0
    print(f"{len(over)} commit(s) over the {CAP}-line body budget "
          f"CLAUDE.md states:")
    for sha, subject, n in over:
        print(f"  {sha}  {n} lines  {subject}")
    print("\nThe task file is the record - move the argument there and "
          "leave the body saying what changed.")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
