# Round 85 — the rows round 84 left, and the seven it filed against itself

Input: the rows open after [round 84](round-84.md) merged, less
`UX-597`, which the repository's owner asked to leave open. Three of
them — `UX-617`, `UX-620` and `UX-619` — are round 84's own bookkeeping
filed against itself, `UX-619` being `main` going red after that merge.
The rest arrived during the round: seven rows this round filed against
its own work, and six from architecture review 15, which the cadence
guard demanded mid-round at 30 closed rows.

Round 84's finding was that **a filing is a sentence no guard reads**:
six of fifteen premises were false or half-false, and the practice it
left was to re-measure the Motivation and paste the result before
writing any code. Round 85 ran that practice on every item, including
its own filings. What it turned up is one level further in:

> a premise measured once is a measurement; a premise carried forward
> is a sentence again.

**Seven of nineteen premises moved under re-measurement**, and not one
was noticed by the session that wrote it — five of the seven were
written by the orchestrating session from another track's report.

## Decomposition

| track | rows | why together |
|---|---|---|
| — | `UX-604` · `UX-616` · `UX-618` · `UX-619` · `UX-620` | round-84 carry-over and `main`'s red, worked in the orchestrating session |
| orchestration | `UX-617` → `UX-614` → `UX-615` | one helper, one brief, one scratchpad — the round's own machinery |
| contracts | `UX-612` → `UX-610` → `UX-613` | all three touch `bga/schemas.py` |
| gate | `UX-621` | `.github/workflows/ci.yml` and the drift tool, disjoint from both |
| review | architecture review 15 | the cadence guard went red at 30 closed rows mid-round |
| H | `UX-624` | `tools/dev_touching.py` and the selector's ceiling |
| I | `UX-622` → `UX-627` | `tools/dev_close_task.py`, one file, serial |
| J | `UX-623` → `UX-626` → `UX-625` | all three land in `.claude/` and one guard file |

`UX-613` was declined by the contracts track — a new stamped contract
forces a figure in `docs/contributing/release-guide.md`, which the
orchestration track held — and re-run once that track merged. The
decline was right: it saved a batch gate red rather than shipping half
an item.

## What the round found

### Premises that moved under re-measurement

| row | filed | measured |
|---|---|---|
| `UX-610` | `compare/v2` carries 28 keys | **29** — `UX-593` counted without `schema`, which is a key |
| `UX-613` | the refusal names `rate`, `QUANTITIES` and four census guards | it names none; the quoted sentence is `UX-595`'s own **Deviation**, not the tool's output |
| `UX-613` | the schema bundle grows ~5,000 B | **+85 B**, and the bundle carries `analyze/v5` only — that run read the *headroom* as the growth |
| `UX-621` | the log body is served by `productionresultssa1` | the digits vary per run — `sa18` here, `sa19` in `UX-457`; pinning the host was never the reading |
| `UX-624` | the guard is reachable only through the map | it writes `from bga import schemas` nine times; `tokens_for` had no spelling for that form — **253 edges** across the suite |
| `UX-623` | an unpushed round branch leaves the base uncheckable | a linked worktree shares the **ref store**; 75 local-only branches, one resolved by name with no `origin/` counterpart |
| `UX-625` | the `falsify` skill does not say how to revert | it has since `bc15935` — and the recipe it gave **could not run**: `cp` to a nested path under a directory that did not exist |

`UX-612`'s is the one that held in full, and it held hard: a wrapped
log's mtime was **62 days** after its recorded start, and nothing in
the payload distinguished the two.

### The defect the round was producing while it ran

`close_status_line` names four status words. `🔴 Open` entered the tree
on 2026-09-03 and is what every row filed since is written with, so
closing one leaves the old word standing:

```text
in : **Status:** 🔴 Open | **Priority:** Low
out: **Status:** 🟢 Done Open | **Priority:** Low
status_words(out): ['Done']
```

Seventeen files, sixteen of them closed in this window, with
`dev_close_task.py --check` reporting `0 problem(s)` throughout —
because `status_words()` parses with the vocabulary under test, so the
word it cannot name is the word it cannot see. This is `UX-454`'s
"Done Done" defect **reproduced by the fix for it**, and two of that
first occurrence are still quoted in its own file as evidence.

Found by architecture review 15, filed as `UX-627`, and fixed inside
the round — five further rows had already been closed by the old helper
between the sweep and the merge, and were repaired at the gate.

### Guards that did not discriminate

| row | clause | why |
|---|---|---|
| `UX-620` | the staleness clause, under two of four mutations | widening the exclusion makes it **skip**, not fail — fixed by extracting the exclusion as a pure, directly-tested function plus a non-vacuity clause |
| `UX-610` | `every_evidence_path_resolves_in_this_document` | a record built against a *different* document spells the same keys and re-resolves clean; it now asserts the record's own `resolved` flag agrees |
| `UX-615` | `UX-560`'s `the_implementer_takes_its_base_rather_than_stopping` | stopped discriminating under the track's mutations; rewritten |
| `UX-624` | the reporter's first form compared `select()` to itself | true by construction; rewritten to recompute the derivation, with an explicit `len(reachable) > 100` non-vacuity assert |
| `UX-623` | `says_no_when_the_copy_has_diverged` | reads git's exit 128 for an unresolvable ref as a "no" — discriminates against its own gate, not against a broken fixture. Left, and written down |

### An instrument that read a git version

`UX-623`'s `test_the_private_git_dir_carries_no_refs_of_its_own` is
green on git 2.43 and red on CI's 2.55, which creates a private `refs/`
for the per-worktree refs. The directory's existence was a **proxy**
for "the ref store is shared", and the two came apart on a machine this
round never ran on. The property holds on both: `git rev-parse
--git-path refs/heads/round` answers with the *common* dir. That is
fixing guide §5's shape, and it reached `main`'s candidate before CI
caught it.

### Errors of the orchestrating session

Four, all recorded in the files rather than only here.

`UX-619` was **filed on unmeasured evidence** — three consecutive
identical failures and non-reproducibility, neither measured. It failed
identically once, and reproduces in 38s at the commit never tested.

`UX-620`'s closing commit **staged a path that did not contain the
fix** — `git add -u docs/backlog/scenarios/` while the fix lived in
`tests/unit/`. Recorded in `UX-617`, whose shape it is.

The `UX-621` brief **named a base commit that does not exist**:
`git cat-file -t 2a7d1b8` → `fatal: Not a valid object name`. Written
from memory rather than read. The track caught it and resolved the
description instead, which is `UX-614` working on the day it landed;
its own explanation was generous and wrong, and `UX-626` says so.

`UX-624`'s Acceptance Test **quoted the wrong bound** — 25 is
`HANDFUL`, and the ceiling's median is 20.

## Landed

Derived from `closed.md` at the gate, not typed — **18 rows**.

| row | what it was |
|---|---|
| [UX-604](../backlog/scenarios/UX-0604-the-verification-log-clause-reads-the-entry-below.md) | the verification-log clause reads the entry below it |
| [UX-610](../backlog/scenarios/UX-0610-the-verdict-record-is-not-a-published-key.md) | the verdict record is not a published key |
| [UX-612](../backlog/scenarios/UX-0612-the-start-clock-has-no-provenance.md) | the start clock has no provenance |
| [UX-613](../backlog/scenarios/UX-0613-the-capacity-model-emits-no-document.md) | the capacity model emits no document |
| [UX-614](../backlog/scenarios/UX-0614-a-track-starts-on-the-default-branch.md) | a track starts on the default branch, not the round's |
| [UX-615](../backlog/scenarios/UX-0615-the-scratchpad-is-shared-between-tracks.md) | the scratchpad is shared between tracks |
| [UX-616](../backlog/scenarios/UX-0616-the-coupling-runs-the-other-way-too.md) | the coupling runs the other way too |
| [UX-617](../backlog/scenarios/UX-0617-the-derived-count-cannot-see-an-unstaged-row.md) | the derived count cannot see an unstaged row |
| [UX-618](../backlog/scenarios/UX-0618-the-step-that-fails-most-writes-no-record.md) | the step that fails most writes no record |
| [UX-619](../backlog/scenarios/UX-0619-four-small-tier-failures-nobody-can-name.md) | four small-tier failures nobody can name |
| [UX-620](../backlog/scenarios/UX-0620-a-derived-count-re-dates-the-document-it-grounds.md) | a derived count re-dates the document it grounds |
| [UX-621](../backlog/scenarios/UX-0621-a-drift-gate-red-nobody-can-read.md) | a drift-gate red nobody can read |
| [UX-622](../backlog/scenarios/UX-0622-the-derived-count-and-its-guard-read-two-populations.md) | the derived count and its guard read two populations |
| [UX-623](../backlog/scenarios/UX-0623-a-track-cannot-read-the-tree-it-was-copied-from.md) | a track cannot read the tree it was copied from |
| [UX-624](../backlog/scenarios/UX-0624-the-cap-dropped-a-guard-that-was-not-noise.md) | the cap dropped a guard that was not noise |
| [UX-625](../backlog/scenarios/UX-0625-reverting-a-mutation-can-discard-the-work.md) | reverting a mutation can discard the work |
| [UX-626](../backlog/scenarios/UX-0626-a-brief-names-a-commit-nobody-resolved.md) | a brief names a commit nobody resolved |
| [UX-627](../backlog/scenarios/UX-0627-closing-a-row-writes-done-open.md) | closing a row writes `🟢 Done Open` |

Filed and left open for round 86: `UX-628`..`UX-632`, all six of
architecture review 15's, less the one this round fixed.

## The gate

`make test` first ran **14 failed, 6892 passed, 29 skipped, 17
errors**. The seventeen were one file, and the cause was not code:

```text
FAILURE Staging local files into CAS
Cache too full
```

**2.3 GB in 64 merged agent worktrees** under `.claude/worktrees/`,
accumulated across this session's rounds. `df` reads the volume and not
the session's writable allowance, so it showed 13 GB free while
BuildStream refused. Pruned, and the file is **24 passed in 43.91s**
with nothing else changed. Ruled out as this round's diff first: at
round 84's tip the same file *skips*, because the generated toolchain
is gitignored and absent from a worktree.
