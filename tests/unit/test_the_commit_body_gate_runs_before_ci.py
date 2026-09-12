"""UX-764: the commit-body cap CI reads and the suite never calls.

`tools/dev_commit_bodies.py` is only invoked by CI (`ci.yml:642`),
against `origin/main`. Round 106 shipped a ten-line body against the
eight-line cap; it was invisible in the diff and in the track's own
`make test`, and surfaced only when a verifier ran the tool by hand.
This runs the same tool, same population, inside `make test` - a
track's own gate, not a separate job it can outrun.

Population: `origin/main..HEAD`, the commits this checkout adds beyond
its own remote-tracking main. That is the same one CI reads, so a
local run and CI never disagree about what counts, and it is well
defined for a diverged checkout: `A..B` excludes only what `A` can
already reach, not a computed symmetric difference. What it cannot
see: a checkout where `origin/main` does not resolve (CI's own `test`
job, which never fetches it - only `agent-config` does), and a commit
already folded into `origin/main` itself, whose range is then empty by
construction - this is a pre-merge gate, not a retroactive audit.
"""
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import dev_commit_bodies as tool

BASE = "origin/main"


def _base_resolves():
    return subprocess.run(
        ["git", "rev-parse", "--verify", "-q", BASE], cwd=REPO,
        capture_output=True).returncode == 0


@pytest.mark.skipif(not _base_resolves(),
                     reason="origin/main does not resolve in this checkout")
def test_the_checkout_stays_within_the_commit_body_cap():
    over, considered, in_range, _skipped = tool.over_cap(base=BASE)
    assert over == [], (
        f"{len(over)} of {considered} commit(s) considered in "
        f"{BASE}..HEAD are over CLAUDE.md's {tool.CAP}-line commit-body "
        f"cap: {over}. Run `python3 tools/dev_commit_bodies.py {BASE}` "
        f"and move the argument to the task file - the body says what "
        f"changed.")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
