"""UX-998 sweep: a round document cites a commit this clone can reach.

`41ded5ef` was rebased to `12afba7a` and both `round-142.md` and
`agent-runs.md` kept the old hash for a while - a reader following it
finds nothing. Census (`git merge-base --is-ancestor` per backtick-hex
citation, `docs/audits/round-*.md` + `agent-runs.md` rows):

```text
round-9.md   5eda28a    unreachable (also true of every round before 142)
round-134.md a4541d98   unreachable
round-135..144.md, agent-runs.md   all citations reachable
```

Scoped from round 142 on, per that census, not from the first clean
round (135): the item that filed this asked for "at least 142".
"""

import functools
import pathlib
import re
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
AUDITS = REPO / "docs/audits"
AGENT_RUNS = AUDITS / "agent-runs.md"

#: The floor this guard reads from. `UX-998`'s census found round 134
#: still citing an unreachable commit; 142 is where the sweep that
#: filed this item asked the guard to start.
FIRST_CLEAN_ROUND = 142

#: A commit citation, as `dev_audit_reports.py` and
#: `test_the_review_has_a_cadence.py` already read one: backtick-wrapped
#: hex, at least 7 characters.
CITATION = re.compile(r"`([0-9a-f]{7,40})`")

ROUND_FILE = re.compile(r"^round-(\d+)\.md$")
AGENT_RUNS_ROW = re.compile(r"^\|\s*(\d+)\s*\|")


def _round_number(path):
    match = ROUND_FILE.match(path.name)
    return int(match.group(1)) if match else None


def _git(*argv):
    done = subprocess.run(("git",) + argv, capture_output=True, text=True, cwd=REPO, timeout=60)
    return done.returncode, done.stdout.strip()


def _shallow():
    return _git("rev-parse", "--is-shallow-repository")[1] == "true"


def _reachable(sha):
    """Ancestor of HEAD, by the definition `merge-base --is-ancestor`
    gives it. A sha this clone has never held at all (a rebased-away
    hash, `41ded5ef`'s own case) fails exactly the same way a real,
    merged-elsewhere sha does - both are "this clone cannot get there"."""
    return _git("merge-base", "--is-ancestor", sha, "HEAD")[0] == 0


def round_citations():
    """`{round-NNN.md: {citation, ...}}` for every round >= FIRST_CLEAN_ROUND."""
    found = {}
    for path in AUDITS.glob("round-*.md"):
        n = _round_number(path)
        if n is None or n < FIRST_CLEAN_ROUND:
            continue
        cites = set(CITATION.findall(path.read_text(encoding="utf-8")))
        if cites:
            found[path.name] = cites
    return found


def agent_runs_citations():
    """`{lineno: {citation, ...}}` for rows whose round >= FIRST_CLEAN_ROUND."""
    found = {}
    for lineno, line in enumerate(AGENT_RUNS.read_text(encoding="utf-8").splitlines(), start=1):
        match = AGENT_RUNS_ROW.match(line)
        if not match or int(match.group(1)) < FIRST_CLEAN_ROUND:
            continue
        cites = set(CITATION.findall(line))
        if cites:
            found[lineno] = cites
    return found


@functools.lru_cache(maxsize=1)
def _unreachable():
    """Every cited commit that is not an ancestor of HEAD, as
    `(where, sha)` pairs."""
    problems = []
    for where, cites in round_citations().items():
        for sha in sorted(cites):
            if not _reachable(sha):
                problems.append((where, sha))
    for lineno, cites in agent_runs_citations().items():
        for sha in sorted(cites):
            if not _reachable(sha):
                problems.append((f"agent-runs.md:{lineno}", sha))
    return problems


class TestACommitCitationReachesHead:
    def test_round_documents_from_142_cite_only_reachable_commits(self):
        if _shallow():
            pytest.skip(
                "this checkout is shallow, so its history stops at a "
                "boundary and reachability here is not the tree's answer"
            )
        bad = [f"{where} {sha}" for where, sha in _unreachable()]
        assert bad == [], f"commit citation(s) no clone of this branch can reach: {bad}"

    def test_the_population_is_not_empty(self):
        """Non-vacuity: round 142 alone carries multiple citations."""
        cites = round_citations().get("round-142.md", set())
        assert len(cites) >= 1, "round-142.md's citations were not found"
