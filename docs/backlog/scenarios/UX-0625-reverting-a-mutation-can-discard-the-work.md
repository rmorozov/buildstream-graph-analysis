# UX-625: reverting a mutation can discard the work

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-560 (the track's recovery), UX-614 (the base check) | **Found by:** round 85, by the UX-621 track paying for it | **Serves:** a track falsifying its own guard | **Topic:** guards

## Motivation

**Corrected round 85, by measurement — the filed text is kept below.**
"It does not say how" is false. The skill has said how since `bc15935`
(`UX-359`), in two places: step 1 of the loop is `cp <file>
/tmp/<file>.bak`, and a paragraph names `git checkout --` as a trap.

The defect is that the recipe **does not run**. `/tmp/<file>.bak` for
any file below the repository root is a path whose directories do not
exist:

```text
$ cp .github/workflows/ci.yml /tmp/.github/workflows/ci.yml.bak
cp: cannot create regular file '…': No such file or directory   exit 1
$ cp tests/unit/test_the_agent_configuration_holds.py /tmp/…
cp: cannot create regular file '…': No such file or directory   exit 1
```

Every file in this repository is below the root, so step 1 fails for
every mutation anyone will ever apply. A track that runs it verbatim,
gets an error, and improvises reaches for the one command that looks
equivalent — which is how `git checkout --` was reached, not from the
skill being silent.

Two more, found while reading it:

- the heading says **Two** failure modes and three paragraphs follow,
  so the safe-revert rule sits where a reader counting two stops;
- `/tmp` is shared between tracks. `UX-615` measured one scratchpad
  for the whole project with `mutate.py` overwritten mid-round; a
  flattened `/tmp/ci.yml.bak` collides the same way.

### As filed (round 85)

The `falsify` skill says apply the mutation, watch it redden, revert
it. It does not say **how**, and one obvious how is wrong:

```text
$ git checkout -- .github/workflows/ci.yml     # revert mutation 1
  … also discards the track's own uncommitted edit to that file
$ pytest …                                     # mutation 2
  2 failed — one of them a false red, diagnosed as a real one first
```

A track's working tree is the only copy of work that is not yet
committed, and the mutation is applied to the same file the work is
in. `git checkout --` cannot tell them apart. The UX-621 track lost
its `ci.yml` edit this way and worked around it with file copies into
the scratchpad.

The cost is not the lost edit — that is a minute. It is the false red
in the next mutation's run, which reads exactly like a guard that does
not discriminate, and is the one reading this repository takes most
seriously.

## Required Fix

**Corrected with the premise.** The skill's own recipe works: a
snapshot path whose directories exist, that does not collide between
tracks, and a revert that reads it back. The heading counts its
paragraphs, and `implementer.md` — which is what a track actually
reads at mutation time — names the trap rather than saying only
"revert the mutation".

### As filed (round 85)

Either the skill says what a safe revert is — snapshot the file first,
or apply the mutation as a patch and reverse-apply it — or a helper
does it, so the track does not have to have been bitten once to know.

Whichever, the argument is that the mutation and the work occupy the
same file, and no `git` revert command distinguishes them.

## Out of Scope

- The mutation discipline itself — right, and unchanged.
- `UX-560`'s recovery, which is about the base, not the desk.

## Acceptance Test

A mutation applied to a file the track has already edited, reverted,
and the track's own edit still present.

## Outcome (round 85, 2026-09-04) — 🟢 Done

**Premise: half falsified — the skill was not silent, its recipe was
broken.** The mechanism is confirmed and the remedy moves.

### The gap, measured

`git checkout --` does what the row says. Reproduced on a sandbox
repository, an edit and a mutation in one file:

```text
1. the track's own uncommitted edit   original / THE TRACKS OWN EDIT / line two
2. the mutation, same file            original / THE TRACKS OWN EDIT / MUTATION
3. after `git checkout -- ci.yml`     original / line two
   git status --porcelain             ''      ← both gone
```

But the skill has said to snapshot since `bc15935` (`UX-359`). What it
had not done was work — step 1 verbatim, for the file the `UX-621`
track was mutating and for this round's:

```text
$ cp .github/workflows/ci.yml /tmp/.github/workflows/ci.yml.bak
cp: cannot create regular file '…': No such file or directory   exit 1
```

Every file here is below the root, so step 1 failed for every mutation
anyone would ever apply, and `git checkout --` is what a track reaches
for when the documented step errors. Two more found while reading: the
heading said **Two** failure modes over three paragraphs, and `/tmp`
is the shared location `UX-615` closed.

### After

The loop snapshots into `<scratchpad>/$(basename "$PWD")/<file>` after
`mkdir -p "$(dirname …)"` — nesting-safe and per-track. The heading
counts. `implementer.md` step 5, which is what a track reads at
mutation time, names `git checkout --` as the trap and step 1 as the
revert.

```text
$ python -m pytest …TestTheDocumentedRevertKeepsTheTracksOwnWork -q
5 passed, 122 deselected in 0.26s
$ make test-touching   18 file(s) selected · 608 passed, 3 skipped in 32.67s
```

**No helper.** A track that never opened the skill would not run a
helper either, and the trap was reached by following step 1 and
finding it broken — a tool does not fix a recipe. It would also cost a
`tests/tiers.py` row and a CI-seconds row, both merge hotspots, for a
`cp`. The argument the Required Fix asked for is that the mutation and
the work occupy one file and no git command separates them; that
sentence is now in the skill's third failure mode.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| C1 | step 1 back to `/tmp/<file>.bak`, as filed | 3 of 5, each on the real `cp: cannot create regular file` — the regression case |
| C2 | `$(basename "$PWD")` dropped from the snapshot path | `…two_tracks_snapshotting_one_file_do_not_collide` only: `['agent-bbbb'] != ['agent-aaaa', 'agent-bbbb']` |
| C3 | heading back to "Two" | `…heading_counts_the_failure_modes_under_it`, `assert 2 == 3` |
| C4 | step 5 softened to "from the copy you kept" | `…told_which_revert_at_the_step_it_reverts`, 1 of 5 |
| C5 | C4 **plus** the phrase planted outside the loop section | still red — the clause reads the subject, not the file |

C5 is the `falsify` skill's own scoping test and the reason C4 counts:
without it, "names the trap somewhere in the body" would have passed.

C1 reddens three because restoring the filed recipe removes the one
property all three rest on — that step 1 executes. Recorded rather
than split.

No guard of this item failed to discriminate.

### Deviation from the Required Fix

The Required Fix was corrected with the premise. Its first option is
taken and the helper declined, with the argument above.
