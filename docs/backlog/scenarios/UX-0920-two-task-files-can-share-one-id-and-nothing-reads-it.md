# UX-920: two task files can share one backlog id, and no guard reads ids for uniqueness

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-501 | **Found by:** four concurrent PRs on 2026-09-21 filed six rows under four ids; `UX-917` and `UX-918` each name two unrelated defects | **Serves:** every round that runs more than one branch at a time, which is now the normal case | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

A backlog id is the repository's only handle on a task: `--move` finds
a row by it, `closed.md` links by it, the fixing guide cites by it and
a later round reads the file instead of the code. Nothing checks that
one id names one file.

Measured on the four PRs open at 17:40 on 2026-09-21
(`git ls-tree -r --name-only pr/<n> -- docs/backlog/scenarios`):

```text
#248  UX-0917-the-fold-depth-guard-has-three-unconfirmed-excursions.md
      UX-0918-the-wrapper-shims-need-coreutils-a-staged-sandbox-has-not-got.md
#249  UX-0917-hidden-findings-keep-live-controls.md
      UX-0918-snapshot-navigation-and-management-need-separate-loci.md
#250  UX-0917-the-fold-depth-guard-has-three-unconfirmed-excursions.md
#251  UX-0919-the-fold-guard-has-three-unconfirmed-excursions.md
```

Two separate failures sit in that table.

**The silent one.** `#249`'s two rows are different *defects* under the
same two ids as `#248`'s, with different filenames. Git has no conflict
to report — two new files, two new index rows — so both merge clean and
the directory then holds two `UX-917`s. `dev_close_task.py --check`
reads glyphs and derives counts; it never asks whether an id appears
twice, so the counts stay correct while the handle stops being one.

**The noisy one.** Three of the four filed the same defect — `main`'s
flake-ledger guard — as `UX-917` twice and `UX-919` once. That is not
an id collision but its cause: a thread with no view of what another
thread just filed picks the next free number from its own checkout.

The `#250` line is the benign case worth keeping in view: same id,
same filename, so git either merges it identically or conflicts
visibly. The guard this row asks for is for the other two rows.

## Required Fix

A guard over `docs/backlog/scenarios/` that reads the id out of each
filename and each file's own `# UX-NNN:` heading, and fails when an id
names more than one file, or when a file's heading and its filename
disagree. It belongs beside the derived-count check in
`tools/dev_close_task.py --check`, so one command still answers "is the
backlog well-formed", and the guard mutates against a second file
written under an id that already exists.

The allocation half — how a thread picks an id no sibling thread has
taken — is a process question and not this row's; note it in the
Outcome if the guard's own failure mode suggests an answer.

## Out of Scope

- Renumbering any row now open. `#248` is the earliest filing, so it
  keeps `UX-917` and `UX-918`; the other branches drop or renumber
  their duplicates. This row adds the check, it does not resolve the
  four PRs.
- The duplicate filings of the flake-ledger defect. Those are
  `UX-908`'s and `UX-917`'s territory.
- Any change to how ids are *allocated*. Declined here rather than
  filed: the guard's own failure mode is the evidence a proposal would
  need, and it does not exist yet, so a row opened now would carry a
  hypothesis instead of a measurement. The Required Fix says to note
  it in the Outcome if the guard suggests an answer.

## Acceptance Test

With the guard in place, adding a second file under an id already in
the directory fails `--check` and names both paths:

```text
$ python3 tools/dev_close_task.py --check
UX-917 names two files:
  docs/backlog/scenarios/UX-0917-the-fold-depth-guard-has-three-unconfirmed-excursions.md
  docs/backlog/scenarios/UX-0917-hidden-findings-keep-live-controls.md
```

and the mutation that must redden it is exactly that: write the second
file, expect the failure; remove it, expect silence. A run over the
directory as it stands today must be silent, since `#248` alone holds
no duplicate — so the guard is proved by the mutation and not by the
tree.

## Outcome

**Round 138, 2026-09-23**

**Premise:** held — a second full-header file under `UX-917` passes the
tool as it was.

### The gap, measured

`UX-917`'s first 80 lines copied to
`UX-0917-hidden-findings-keep-live-controls.md` (heading retitled), and
`HEAD`'s tool pointed at this tree:

```text
$ python3 <HEAD's dev_close_task.py> --check --scenarios docs/backlog/scenarios
0 problem(s) over 10 propert(y/ies), 940 backlog row(s)
```

Two files, one id, nothing asked; `task_file` answers with whichever
sorts first.

### After

An eleventh `--check` property, `id_problems()` in `tools/_close_task_checks.py`: each filename's id
against every other file's, and each file's first `# ` heading against
its own filename.

```text
$ python3 tools/dev_close_task.py --check        # the same second file
  FAIL  every id names one task file, and its heading names that id - 1 problem(s)
          UX-917 names 2 files: docs/backlog/scenarios/UX-0917-hidden-findings-keep-live-controls.md,
          docs/backlog/scenarios/UX-0917-the-fold-depth-guard-has-three-unconfirmed-excursions.md
$ rm docs/backlog/scenarios/UX-0917-hidden-findings-keep-live-controls.md
$ python3 tools/dev_close_task.py --check
0 problem(s) over 11 propert(y/ies), 940 backlog row(s)
```

The tree: 940 files, 940 ids, no duplicate, 940 headings agreeing.
`UX-22`'s heading is its third line, under a supersession note, so the
first `# ` line is read rather than line 1. A heading naming a taken id
names both paths: `UX-0999-...md: heading says UX-917, filename says
UX-999; UX-917 is docs/backlog/scenarios/UX-0917-the-fold-...md`.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| C1 | the duplicate clause's `len(paths) > 1` made `> 99` | 1 of 3: `test_a_second_file_under_an_existing_id_fails_naming_both` |
| C2 | the heading comparison made `elif False:` | 1 of 3: `test_a_heading_that_names_another_id_fails_naming_both` |
| C3 | the second file written into this tree | 2 of 3: `test_the_tree_is_silent`, and the heading clause (its copy now holds two problems) |

### What the failure mode says about allocation

The guard fires only on a tree holding both files - after a merge or a
trial merge. A thread taking the next free number from its own checkout
cannot see a sibling's filing, so this is a backstop, not an allocator.
Round 138 gave each parallel track a **disjoint id range** in its brief
(this track: `UX-945`..`UX-949`), which removes the collision at the
source; that is the practice to name, and this guard catches a track
that files outside its range.

### Deviation from the Required Fix

None. The duplicate prints as one line naming both paths, not the
Acceptance Test's three-line block: `--check` prints a problem per line.

```text
$ make test-touching     # taken with UX-935's and UX-932's rows moved, since withdrawn
1 failed, 2235 passed, 4 skipped in 303.45s   # the review cadence: 27 closes since review 25, bound 25
```
