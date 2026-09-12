# UX-814: the map's commit-body row is behind the App-author skip

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-811 (the mechanism) | **Found by:** round 113, review 22 | **Serves:** the reader pricing a change from §6 | **Topic:** docs | **Area:** tools | **Shape:** mechanical

## Motivation

`docs/contributing/fixing-guide.md` §6's row for
`tools/dev_commit_bodies.py` says "which of a branch's commits spend
more than eight body lines, footer excluded (UX-696)". `UX-811` made
the tool skip a GitHub App's commit and count it; the module docstring
says so, the map does not:

```text
$ grep -n "dev_commit_bodies" docs/contributing/fixing-guide.md
373:tools/dev_commit_bodies.py   which of a branch's commits spend more than
$ sed -n 16,17p tools/dev_commit_bodies.py
would go stale the first time this branch is merged. A GitHub App's
commit (`UX-811`: Dependabot's generated release notes) is skipped and
```

## Required Fix

The row names the skip and cites `UX-811` beside `UX-696`.

## Out of Scope

- The map's other rows — review 22 checked `dev_sizes.py` and
  `dev_baseline.py` and found them current.

## Acceptance Test

`grep -n "UX-811" docs/contributing/fixing-guide.md` names the row;
`make lint` clean.

## Outcome

**Close measured.**

```text
$ grep -n "UX-811" docs/contributing/fixing-guide.md
375:                             App's skipped and counted (UX-696, UX-811)
```

**Deviation.** None. A one-row edit; no guard reads the row's prose,
so no mutation — review 22 is the check.
