# UX-241: architecture review has no cycle

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-233 (the drift guard), UX-237 (the filing rule) | **Serves:** R8, and the maintainers pricing the next big change | **Topic:** docs

## Motivation

The user's last observation: *regarding keeping documentation updated
and architecture flexible we need regular cycles of architecture and
documentation state review to place new tasks.*

`UX-233` fixed the drift once and guarded the mechanical half — every
published schema id must appear in the spec and the architecture
inventory. What it cannot catch is the half that matters most: a
*chapter* that describes a mechanism the code no longer has. The
architecture document went a whole axis out of date (rounds 21-26,
about 250 commits) before anyone noticed, and nothing in the process
would have noticed it sooner.

Feature audits happen here on a cadence — twenty-eight rounds of them.
Architecture and documentation review does not, and the asymmetry is
why one drifts and the other does not.

## Required Fix

1. **A review is a round type**, described where the streams are
   (`UX-239`): its input is the diff since the last review, its output
   is filings, and it produces no code.
2. **A checklist with teeth**: for each architecture chapter and each
   guide, does the code still do what it says; does every published
   contract have a home; is any figure invalidated; what shipped since
   the last review with no document naming it.
3. **The trigger is measured, not remembered.** A guard reports the
   distance since the last recorded review — commits, and rounds — and
   reddens past a stated bound, the same way the store's size warning
   works. The bound is a decision to argue for, not a number to guess:
   round 28's evidence says one axis is too long.
4. The review's output goes in `docs/audits/` like every other round,
   so the next one can measure against it.

## Out of Scope

- Reviewing the spec's Part text. It is ground truth and the fixing
  guide forbids editing it; a review that finds it wrong files against
  it instead.
- Automating the judgment. The guard measures *distance since*, never
  whether a chapter is true.

## Acceptance Test

The review round type is described with its input, output and
checklist; the distance guard reports a real number on this tree and
reddens past the bound (verified by moving the recorded marker back);
the first review is run and its filings land.

## Outcome

**Status:** 🟢 Fixed & Verified

Review is a seventh stream in `§6a`, and
[`docs/audits/architecture-review.md`](../../audits/architecture-review.md)
carries what it is — input, output, checklist, log — beside the six
that were already named. One rule in it does the work of keeping a
review a review: **it produces no code.** A session that fixes what it
finds is a fix session wearing a review's name, and stops being able to
see the next thing.

### The cadence is a number in the tree

`tests/unit/test_the_review_has_a_cadence.py` reddens when more than
**25 scenarios** have closed since the last logged review.

Closed rows rather than commits, for two reasons that are both
measurements rather than taste. A commit is not a unit of change here —
this round alone is five commits and one range — so a commit bound
would fire on a busy week and stay quiet through a slow drift. And the
count is in `closed.md`, so the guard needs no `git` and answers the
same on every machine, which is the property `UX-213` was filed over
when guards turned out to only guard one.

The bound is argued against the drift that was actually missed: the
viewer axis ran `UX-193`..`UX-226`, **34 closed rows**, with nothing in
the process to notice. 25 would have caught it with room; 34 would only
just have. The document states the same number the guard enforces, and
a guard checks that too, because two copies of one number is the defect
this repository fixes more often than any other.

### The first review ran, and found three things

Not a template with an empty log — the item's acceptance test asked for
the first review, and the review is what produced `UX-245`..`UX-247`:

```text
subcommands in `bga --help`, absent from "## Real current CLI surface":
  blast    shipped round 19 (UX-172)
  whatif   shipped round 28 (UX-230)

subcommands absent from docs/guides/real-project.md:
  whatif, cache-trend, diagnostics, floors, graph, utilisation
  (five are correct - a journey is not a reference; whatif is not)

docs/design/architecture.md "## Verification Log":  "Updated 2026-08-18"
git log -1 --date=short:                            2026-08-23
```

Five commits have touched `architecture.md` since the line claiming
2026-08-18 was written. That is the smallest finding and the worst
shape — a document's claim *about its own currency* being false — and
it is exactly the kind a guard cannot see and a checklist can.

What was checked and found current is recorded too, because a review
that only lists problems cannot be compared against the next one: every
published schema id is in spec Part 32.5 and the architecture inventory
(guarded since `UX-233`), the three planes' chapters match the modules
they name, the 33% five-capture noise figure is round 9's, and `cli.md`
names every subcommand and every `tools/` alias.

### One thing the review found in the guide it was being written into

`§6a`'s documentation row pointed at `§4a.9` for the doc-gap rule.
`§4a` has six items, and the rule is `§3.11` — a dangling
cross-reference written one item earlier in this same round. Corrected.

**Mutations verified red and reverted (7):** the review document
missing its input/output/done-when; `review` dropped from the stream
table; the "produces no code" rule deleted; the log emptied of rows;
the recorded row count moved back past the bound; the bound in the
document disagreeing with the guard; a review row with no findings.

**Deviation from the Required Fix:** clause 3 asked for the distance in
"commits, and rounds". The guard measures closed rows only, for the
reasons above — a git-dependent guard is one this repository has
already been bitten by, and rounds have no in-tree marker of their own.
The review log records the commit sha, so the git distance is
recoverable by hand when someone wants it; it is just not what reddens.

Small tier: `2033 passed, 1130 deselected in 20.18s`.
Full suite: `3160 passed, 3 skipped in 309.29s`. `make lint`: clean.

**A hygiene deviation of my own, recorded rather than quietly fixed:**
`§4a.1` says never `git add -A`, and the three commits before this one
used it. Nothing stray was staged — checked against `git show --stat`
for all three, and `make check-clean` is OK — but "it happened to be
fine" is not the rule, and this commit stages explicitly.
