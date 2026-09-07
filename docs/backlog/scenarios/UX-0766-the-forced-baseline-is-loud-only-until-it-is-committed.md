# UX-766: the forced baseline is loud only until it is committed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-745 (which built the visibility) | **Serves:** the session reading `make lint` and believing the baseline did not grow | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-745` found that a track could authorise its own baseline growth
with every gate green, and chose visibility over refusal — its Outcome
says so: *"Making the growth loud in the output the session reads
discriminates where a self-declared reason does not."*

The loudness does not survive the commit that carries it.
`gained_since_head` compares the working tree against `HEAD`. While
the forced entry is uncommitted the two differ and `--check` prints
`authorised by UX-NNN, red until committed`. Once committed they are
identical, and the same command says:

```console
$ python3 tools/dev_baseline.py --check
clean: 293 finding(s) match tests/quality_baseline.json
```

Round 105 walked into it. `UX-762`'s track ran `--force --reason
UX-762` for two `S607` entries and committed them; `make lint` is
green and silent, and its verifier found the growth only by reading
`git diff tests/quality_baseline.json` by hand. `UX-745`'s own
motivating example is a track doing exactly this.

So the safeguard works for the author, in the minutes before they
commit, and for nobody afterwards — not the reviewer, not CI, not the
next round. The one reader it was built for is the one it does not
reach.

## Required Fix

Make an authorised growth legible **after** it lands. The baseline
already records `forced` and `forced_by`; nothing reads them back. The
cheapest honest route is a guard that reports every forced entry still
present, so a session sees the standing count rather than a silence —
the shape `UX-745` chose, extended past the commit boundary.

Then decide the follow-through `UX-745` deferred: whether a forced
entry that outlives its own row's close is a debt with a name, or
stays indefinitely.

## Out of Scope

- Refusing a track the ability to force — `UX-745` considered and
  declined that ("Route two ... was **declined**"), and this row does
  not reopen the decision, only its stated visibility.
- The two `S607` entries `UX-762` added — they are the same
  `subprocess.run(["git", ...])` shape already baselined for six other
  tools, and correct on their merits.

## Acceptance Test

A committed forced growth is visible in the output a session reads,
not only in a hand-read diff. Mutation: force an entry, commit it, and
confirm the check names it where today it prints `clean`.

## Outcome

**The gap, measured.** Before this row, on the tree that already
carries UX-762's own forced S607 pair, committed:

```console
$ python3 tools/dev_baseline.py --check
clean: 293 finding(s) match tests/quality_baseline.json
```

**The close, measured.** `do_check` now names every `forced` identity
still present in the baseline, excluding whatever `authorised` already
names pre-commit so a line is never printed under both banners:

```console
$ python3 tools/dev_baseline.py --check
still forced by UX-762: ruff S607 .claude/hooks/gate_covers_push.py (#1) done = subprocess.run(["git", "rev-parse", "--show-toplevel"],
still forced by UX-762: ruff S607 .claude/hooks/gate_covers_push.py (#1) done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
clean: 293 finding(s) match tests/quality_baseline.json; 2 still forced by UX-762
```

Exit code unchanged (0): this is visibility, not a new refusal — `--force`
stays available (`UX-745`'s declined route stands).

**The decision.** Stays indefinitely, named by the reason that signed
it. `--shrink`/a plain `--write` drop it only once the identity leaves
`findings` (the code was actually fixed) - the deliberate route to
retire the debt. Auto-expiry keyed to a row's status would read
`closed.md` as a proxy for the real question, which the Out of Scope
already answers for these two lines ("correct on their merits").

**Found by verification, fixed here.** The first cut stored one
`forced_by`/`forced` slot, overwritten whole on every `--force`, so
"stays indefinitely" was false one force-cycle later: force `UX-OLD`,
commit, force an unrelated `UX-NEW`, and `UX-OLD` silently dropped out
of `still forced` while its lines sat unreviewed in `findings` - the
live baseline's own `UX-762` batch was one such write away from that.
`write_baseline` now stores `forced_batches`, a list of
`(reason, identities)` accumulated across writes and pruned only of
identities `_prune_forced` no longer finds in `findings`; `do_check`
names every batch still present, and `gained_since_head` pairs each
gained finding with the reason that actually signed it.

### Mutations verified red and reverted (3)

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | `standing_forced` returns `[]` unconditionally | entry + accumulate tests | 2 of 4 failed |
| M2 | drop the `exclude` filter from `standing_forced` | `test_an_uncommitted_forced_entry_is_not_double_named` | 1 of 4 failed |
| M3 | `do_write` replaces the batch list instead of appending | `test_a_second_unrelated_force_does_not_silence_the_first` | 1 of 4 failed |

All three reverted from the scratchpad copy (never `git checkout --`),
then re-verified green: `tests/unit/test_forced_stays_named_past_commit.py`
(4 passed) plus the pre-existing `test_the_baseline_only_shrinks.py`,
`test_baseline_set.py`, `test_baseline_noise_band.py` (61 passed total).

**`BGA_SKIP_SELECTOR=1`** on the commit: the new test file moves
`fixing-guide.md`'s derived test-file count
(`test_the_cost_row_is_derived_from_the_selector.py`), out of scope for
this track beyond UX-767's one sentence — `dev_touching.py --spread
--write` is the orchestrator's, once, after every track's new files
land this round.
