# UX-694: a finding baseline, and a size ledger for what has no identity

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-693 (the rule set), UX-418 (the reference method) | **Serves:** the implementing session, whose gate is zero-tolerance for a new finding from the first commit and never asks it to fix an old one first | **Topic:** guards

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
