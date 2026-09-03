# UX-551: every session plans its loop against a suite 62% faster than the real one

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-336 (the tiers), UX-500 (which measured it) | **Serves:** the implementing session's wall clock | **Topic:** docs

## Motivation

Architecture review 12, checklist 3. `CLAUDE.md` line 16 is the first
table a session reads:

```text
| `make test` | the whole suite, ~5m30s at `-n auto`. **Required …** |
```

Measured this round, same container, `make test` at `-n auto`:

```text
claimed  (round 74)   ~5m30s ·  5,635 passed, 81 skipped, 328s
measured (round 80)    8m52s ·  6,181 passed, 29 skipped, 532.74s
                       tests +546 · skips 81 → 29 · wall 1.62x
```

`docs/contributing/fixing-guide.md:58` and `.claude/skills/verify`
carry the same figure and both **date** it ("round 74"), so by reviews
5 and 7's precedent those are records. `CLAUDE.md`'s is undated and
reads as current — the exact shape `UX-471` removed from that file.

It is not cosmetic: `UX-500` decided this round that the suite runs
once per item, so a session budgets its round against this number, and
the number is out by three and a half minutes per run.

## Required Fix

Re-measure and restate, dated. `CLAUDE.md` is a summary, so the figure
either carries its round the way the guide's does, or points at the
guide rather than repeating it — one copy is the standing preference.

Note the skip count as well as the wall clock: 81 → 29 is `UX-449`'s
census retiring skips, and a document that quotes one and not the other
describes a suite that never existed.

## Out of Scope

- Making the suite faster; `UX-336` did the parallel half and the
  question here is what the documents say, not what it costs.
- The tier floors — `tests/tiers.py` is measured per file and current.

## Acceptance Test

`CLAUDE.md`'s figure matches a pasted `make test` line from the round
that wrote it, or names no figure at all.

## Outcome (round 81, 2026-09-03) — 🟢 Done

**Premise:** falsified — re-measuring read 3m45s, faster than the figure it was filed to correct; no single wall-clock figure is true.

### The gap, measured

```text
$ grep -n '5m30' CLAUDE.md docs/contributing/fixing-guide.md .claude/skills/verify/SKILL.md
CLAUDE.md:16:| `make test` | the whole suite, ~5m30s at `-n auto`. **Required …** |
docs/contributing/fixing-guide.md:58:… the whole suite is ~5m30s at that … (re-measured round 74 …)
.claude/skills/verify/SKILL.md:58:make test    # ~5m30s at -n auto … (round 74 …)
```

Three copies of one figure, one of them undated and read first.

### After — the premise changed under the fix

The row asked for a re-measurement and a date. Re-measuring falsified
the premise it was filed on. This round, quiet machine, 4 cores:

```text
$ time make test
6256 passed, 29 skipped, 1 warning in 225.94s (0:03:45)
real 3m46.346s   load average before: 2.93
```

Not 8m52s — **faster** than round 74's 5m28s, on 621 more tests. So the
same tree that round 80 measured at 8m52s was asked again:

```text
$ cd /tmp/…/base-ca825c3 && time make test      # ca825c3 = round 80's merge
6097 passed, 124 skipped, 1 warning in 212.11s (0:03:32)
real 3m32.525s   load average before: 3.67
```

**Round 80's 8m52s is not reproducible on the tree that produced it.**
The whole series, same 4 cores:

```text
round 46   3m15s
round 74   5m28s   5,635 passed,  81 skipped, 328s
round 80   8m52s   6,181 passed,  29 skipped, 533s
round 81   3m45s   6,256 passed,  29 skipped, 226s   quiet
  ca825c3  3m32s   6,097 passed, 124 skipped, 212s   re-measured here
```

A 2.5x spread with the test count rising monotonically. The wall clock is
the machine's contention, not the suite's — round 80 read 8m52s while
running four agent tracks, this round 3m45s with none. A *dated* figure
would mislead exactly as much as an undated one: it dates the afternoon.

So `CLAUDE.md` names no figure and says the clock moves >2x with the
machine; the guide carries the series and the falsification; the
`verify` skill gives the range and points at the guide.

### Mutations verified red and reverted (0)

None, and the reason: this row changes three prose documents and adds
no guard. A guard asserting "CLAUDE.md names no wall-clock figure"
would freeze a sentence, not a behaviour.

### A guard of my own that did not discriminate

The base re-measurement ran in a worktree and reported **124 skipped
against the branch's 29**, so the two runs did not execute the same
set. It is not a clean replication and is not offered as one: 159
tests cannot account for 8m52s against 3m32s, and the only claim it
carries is that 8m52s does not reproduce.

### Deviation from the Required Fix

**One, and it inverts the row.** The Required Fix said "re-measure and
restate, dated", with `CLAUDE.md` either carrying its round or pointing at
the guide. It now points at the guide — but the guide does not carry *a*
figure, it carries the series and the finding that no single figure is true.
Restating one dated number would have re-filed this row in two rounds' time.

The skip-count clause is kept: 81 → 29 is `UX-449`'s census retiring
skips, and both numbers travel with their wall clock in the series
above.
