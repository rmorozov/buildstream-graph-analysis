# UX-694: a finding baseline, and a size ledger for what has no identity

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-693 (the rule set), UX-418 (the reference method) | **Serves:** the implementing session, whose gate is zero-tolerance for a new finding from the first commit and never asks it to fix an old one first | **Topic:** guards | **Shape:** bounded

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

**The gap, measured**: `ruff check bga tools tests .claude/hooks
--select S,C901,PLR0912,PLR0913,PLR0915,SIM115 --output-format json`
had no fingerprint the gate could hold — 12,201 findings before this
tree's own guard test existed.

**The close, measured**: `tools/dev_baseline.py --write` on this tree:

```text
S 11852 · C901 99 · PLR0912 54 · PLR0913 68 · PLR0915 32 · SIM115 113
= 12,218 findings written to tests/quality_baseline.json
```

(12,218 not 12,201: the new guard test file itself carries 17 baselined
findings — asserts and one `subprocess.run` — folded in by the same
`--write`.) `make lint` now ends:

```text
python3 tools/dev_baseline.py --check
clean: 12218 finding(s) match tests/quality_baseline.json
```

Planted `bga/_scratch_ux694_mutation.py` (`subprocess.run(cmd,
shell=True)`), removed after:

```text
new: ruff S602 bga/_scratch_ux694_mutation.py (#1) subprocess.run(cmd, shell=True)
```

exit 1; removed, `--check` returned to clean, exit 0.

**Mutations** (`tools/dev_baseline.py`, reverted from a pre-edit copy
each time, `__pycache__` cleared):

| mutation | reddened | count |
|---|---|---|
| identity's `nth` set to the raw line number instead of the per-(rule,file,text) occurrence count | `test_a_line_inserted_above_still_matches`, `test_the_same_line_twice_gives_two_identities` | 2 failed, 4 passed |
| `do_check` exit code ignores `stale`, only reflects `new` | `test_a_fixed_finding_is_reported_as_stale` | 1 failed, 5 passed |
| `do_shrink` appends `new` findings alongside removing `stale` | `test_shrink_never_adds` | 1 failed, 5 passed |

All three reverted to `6 passed`.
