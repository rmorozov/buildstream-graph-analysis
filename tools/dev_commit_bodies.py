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
would go stale the first time this branch is merged. A GitHub App's
commit (`UX-811`: Dependabot's generated release notes) is skipped and
counted: the pull request is its record, not the body.
"""
import re
import shutil
import subprocess
import sys

# S607: resolved once against PATH, not trusted to whatever order the
# shell would have used.
GIT = shutil.which("git") or "git"

CAP = 8
RULE_FROM = "2026-09-06T21:52:00+00:00"
FOOTER = re.compile(r"^(Co-Authored-By|Claude-Session|Signed-off-by|"
                    r"Co-authored-by):", re.I)
APP_AUTHOR = re.compile(r"\[bot\]@users\.noreply\.github\.com$")


def body_lines(body):
    """The lines a body spends, footer and blanks excluded."""
    return [line for line in body.splitlines()
            if line.strip() and not FOOTER.match(line.strip())]


def _log(base, extra):
    out = subprocess.run(
        [GIT, "log", f"{base}..HEAD", "--no-merges",
         *extra, "--format=%H%x1f%s%x1f%ae%x1f%b%x1e"],
        capture_output=True, text=True, check=True).stdout
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if record:
            yield record.split("\x1f", 3)


def over_cap(base="origin/main", cap=CAP, since=RULE_FROM):
    """`(over, considered, in_range, skipped)` for the commits the branch adds.

    Both counts are reported rather than just a verdict: "every commit
    is within the cap" reads the same whether it checked eleven or
    none, and a gate whose population cannot be seen is the defect
    `UX-696` was filed about. A refusal on `in_range == 0` was written
    and then removed - it cannot fire, because an empty `base..HEAD` is
    exactly the case where HEAD is already an ancestor of `base`. What
    catches a failed fetch is `check=True`: an unresolvable `base`
    raises rather than reading nothing.
    """
    in_range = sum(1 for _ in _log(base, []))
    over, considered, skipped = [], 0, 0
    for sha, subject, email, body in _log(base, [f"--since={since}"]):
        if APP_AUTHOR.search(email):
            skipped += 1
            continue
        considered += 1
        n = len(body_lines(body))
        if n > cap:
            over.append((sha[:9], subject, n))
    return over, considered, in_range, skipped



def main(argv):
    base = argv[1] if len(argv) > 1 else "origin/main"
    over, considered, in_range, skipped = over_cap(base)
    if not over:
        print(f"{considered} of {in_range} commit(s) in {base}..HEAD "
              f"checked ({in_range - considered - skipped} predate the "
              f"rule, {skipped} by a GitHub App); "
              f"every one is within {CAP} body lines")
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
