# UX-694: a finding baseline, and a size ledger for what has no identity

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-693 (the rule set), UX-418 (the reference method) | **Serves:** the implementing session, whose gate is zero-tolerance for a new finding from the first commit and never asks it to fix an old one first | **Topic:** guards | **Shape:** bounded

## Motivation

Every stronger tool finds signal today's gate cannot see, and none of
it can reach zero in one commit — the round's first draft therefore
proposed a per-file *count* that may not grow. The user's correction:
a count lets a new finding in whenever an old one leaves the same
file, and cannot say which finding is new. The known trick is a
**baseline**: every current finding written down by identity, the gate
red on any finding not in it, the list only ever shrinking. Measured:

```text
ruff check bga tools --select UP,S,C901,B,SIM,PLR0912,PLR0913,PLR0915 --output-format json
1,709 findings; identity = (rule, file, the line's text, nth occurrence)
1,709 distinct — 298 need the occurrence index; none the line number
ruff --output-format sarif: no partialFingerprints (GitHub hashes the line itself)
pyright 270 · bandit -ll 16 · eslint 70: the same identity applies
```

What has no finding identity — a file's length, a function's length,
a duplicate block — stays a count.

## Required Fix

`tools/dev_baseline.py`: runs `ruff` (json, the baselined families),
`pyright --outputjson`, `bandit -f json`, and `eslint -f json` when
`node` is present; normalizes each finding to `(tool, rule, file,
line text, nth)`; writes `tests/quality_baseline.json`, sorted, one
entry per line so a diff reads. `--check` fails on a finding not in
the baseline **and** on an entry nothing matches any more — a stale
entry is removed in the commit that fixed it, never left. `--shrink`
is the one write; adding an entry needs `--force` and a `UX-` id in
the commit, and a guard reads `git diff` of the file to hold that it
lost lines and gained none. `make lint` runs `--check`; CI uploads
the same run as SARIF to code scanning, the public repository's free
view of the same list. **The size ledger**, `tests/quality_reference.json`:
per file, longest function, lines, duplicate blocks (`pylint
--enable=duplicate-code`); may not grow; `--adopt` rewrites a cell
that shrank, in the same commit (`UX-418`'s pattern). Its top rows
are the refactor stream's queue (`UX-695`); the baseline's are the
burn-down's (`UX-705`).

## Out of Scope

- A target below today's numbers — the baseline's direction is the
  policy; the pace is `UX-705`'s and `UX-695`'s.
- Test files in either — `UX-690`'s shape budget is the suite's
  ledger; one file, one ledger.

## Acceptance Test

`dev_baseline.py --check` passes on the adopting commit; mutation:
add `subprocess.run(cmd, shell=True)` to `bga/cli.py` — red, one
new `S602`; fix one `S607` without `--shrink` — red, one stale
entry; `git diff` that adds a baseline line — the shrink guard red.

## Outcome

**This track lands the baseline half only** — the size ledger
(`tests/quality_reference.json`) is a separate track.

**The gap, measured**: `ruff check bga tools .claude/hooks --select
S,C901,PLR0912,PLR0913,PLR0915,SIM115 --output-format json` had no
fingerprint the gate could hold. The first pass also ran the select
over `tests`, and the verifier caught it: 11,923 of 12,218 written
entries were test-file findings, 11,238 of them `S101` — Out of Scope
says one file, one ledger; `tests` is not a `dev_baseline.py` path.

**The close, measured**: `tools/dev_baseline.py --write --force`,
paths restricted to `bga`, `tools`, `.claude/hooks`:

```text
S 93 · C901 84 · PLR0912 47 · PLR0913 34 · PLR0915 30 · SIM115 11
= 299 findings in tests/quality_baseline.json
```

`make lint` ends `python3 tools/dev_baseline.py --check`; planted
`bga/_scratch_ux694_mutation.py` (`subprocess.run(cmd, shell=True)`) →
`new: ruff S602 ... (#1) subprocess.run(cmd, shell=True)`, exit 1;
removed, clean, exit 0. The verifier's four other fixes land in this
same write: the new git-diff shrink guard reports 6 gained lines right
now against the prior commit's `HEAD` (2 from collapsing interior
whitespace on an already-baselined `bga/contracts.py` `S112` line, 4
from this commit's own new `subprocess.run` calls in `head_findings`)
— the exact case the guard exists for; clean again once this commit is
`HEAD`. `make test-small`: 4,311 passed, 2 known `docs/contributing/`
context-map failures (out of scope, orchestrator's).

**Mutations** (reverted from a pre-edit copy each time, `__pycache__`
cleared):

| mutation | reddened | count |
|---|---|---|
| identity's `nth` = raw line number | 2 tests (line-number, nth) | 2 failed, 4 passed |
| `do_check` exit ignores `stale` | fixed-finding test | 1 failed, 5 passed |
| `do_shrink` appends `new` (no-stale branch) | never-adds test | 1 failed, 5 passed |
| `gained_since_head` disabled | git-diff-guard test | 1 failed, 1 passed |
| `.strip()` instead of whitespace collapse | reformat-still-matches test | 1 failed |
| `do_shrink` appends `new` in the stale branch (verifier's mutation) | stale-and-new-together test | 1 failed |
| `invalid-syntax` check removed | unparsable-file test | 1 failed |

All reverted, `11 passed`.

**Deviation.** The track landed `ruff`'s families only; `pyright`,
`bandit` and `eslint` enter the baseline as `UX-697`, `UX-698` and
`UX-699` land. The size ledger — the half with no finding identity —
is `UX-712`. The orchestrator's brief put `tests/` in the paths against
this task's own Out of Scope, and 11,923 of a first 12,218 entries
were test files, 11,238 of them `S101`; the verifier caught it and the
baseline is 299 over the code. A forced write now needs `--reason
UX-NNN`, written into the header, and a gain is authorised until that
header lands — so the adding commit's own `make lint` is green.

