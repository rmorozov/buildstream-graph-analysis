# UX-587: a guard whose cost is the backlog's size drifts past a reference `--adopt` cannot refresh

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-420 (the reference), UX-488 (the re-record), UX-496 (one run bakes in one sample), UX-503 (the adopt job) | **Found by:** round 83's own CI, blocking PR #200 | **Serves:** every round that files rows | **Topic:** guards

## Motivation

Round 83's second CI run reddened `test (3.11)` on the tier-drift gate,
not on a test:

```text
427 file(s) measured against ci_reference.json (github-actions
ubuntu-latest, test (3.11), -n auto), this run x1.07 from 151 file(s)
over 1s, IQR 0.55, and 1 file(s) slower than ci_reference.json records:
tests/unit/test_docs_links_and_commands.py 18.4s against 10.0s
recorded, x1.73
```

The first run passed and the second failed, which reads like the diff
between them caused it. It is not: that is `UX-442`'s carry, which
confirms a drift only when two consecutive runs agree. Both runs
measured the file slow; the first was the sighting.

The cause is that this guard's cost **is** the size of the backlog it
walks, and the backlog only grows. Measured here, one tree, the task
files moved out and back:

```text
584 task files   13.00s
286 task files    7.47s
```

0.0185 s/file. The reference was re-recorded by `UX-488` at 397 files;
that slope puts the guard at 7.47 + 111 x 0.0185 = **9.5s** then,
against the **9.96** the document actually records. The drift is not
noise and not this branch's: it is four rounds of filings.

`--adopt` cannot correct it. The adopt job "adds names the reference
lacks and rewrites no entry it has" (`ci.yml:351`), by design — so an
entry that exists can only ever go staler, and once two runs confirm,
every PR is red until a person edits the number. `UX-496` recorded the
same ratio (x1.73) on a different file and concluded the gate "was
right to" confirm; what it did not record is that nothing downstream
of the gate can act on it.

## Required Fix

The entry refreshed from the run that measured it, with the reading and
the slope above in the document's note so the next reader sees why it
moved. And the structural half stated where the adopt job is described:
a reference entry for a guard whose population grows is refreshed by a
round, not by `--adopt`, because `--adopt` is add-only on purpose.

## Out of Scope

Making the guard cheaper. It reads every document once, which is what
it is for; 0.0185 s/file over 584 files is the price of the backlog
being checked at all. Whether the gate should re-record confirmed
drifts automatically is a separate decision, and a different item.

## Acceptance Test

```bash
python3 -c "import json; print(json.load(open('tests/ci_reference.json'))['files']['tests/unit/test_docs_links_and_commands.py'])"
```

names the refreshed figure, and `test (3.11)` is green on the head that
carries it.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** held — but the first reading of it was wrong, below.

**The gap, measured.** The gate's own line, run 33746724625, head
`b3ed6e4`:

```text
1 file(s) slower than ci_reference.json records:
tests/unit/test_docs_links_and_commands.py 18.4s against 10.0s
recorded, x1.73
```

**The cause, measured.** One tree, `HEAD`, task files moved out and
back in a throwaway worktree:

```text
584 task files   39 passed in 13.00s
286 task files   38 passed in  7.47s      (1 failed: rows I had removed)
```

0.0185 s/file. `UX-488` re-recorded the reference at 397 files; that
slope predicts 7.47 + 111 x 0.0185 = **9.5s** there, against the
**9.96** recorded. The reference is not wrong about the machine — it
is right about a tree that has since grown by 187 documents.

**The close.** `tests/ci_reference.json`'s entry set to 18.4 from that
run's candidate, and the note extended with the slope and with why
`--adopt` cannot do this itself.

**A reading I got wrong first.** I took run 543 passing and run 544
failing as evidence the drift arrived with `UX-574`, and started
looking at what that item changed. It is `UX-442`'s carry: two
consecutive runs must agree before a drift is confirmed, so 543 was
the sighting and 544 the confirmation. Both measured it slow. A gate
that reports on the second run always looks like the second run's
diff caused it.

**A second reading I got wrong.** I then blamed round 82's 24 new task
files, and an interleaved local A/B refuted it: 584 files read 6.81s
against 550 files at 7.31s, the wrong direction. 24 files is +4%; the
real gap is +47% of the population, four rounds deep. Both readings
are here because the shape — a confirming gate looks like the last
diff's fault — will recur.

**Mutations.** None: this item writes no guard. The clause that would
hold it is the gate itself, which is what reported the drift and is
already mutation-covered by `UX-513`. Recorded rather than skipped.

**Deviation from the Required Fix.** None.

**Suite.** With the batch, at the round's gate.
