# UX-447: the reference-refresh route is in no contributor document

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** review 8, checklist item 4 | **Serves:** the contributor whose PR the drift gate stops, who is told to re-record and not where from | **Topic:** docs

## Motivation

Three items built the route by which `tests/ci_reference.json` gets
refreshed, and none of them put it in a document a contributor reads.

| item | what it built |
|---|---|
| `UX-420` | the reference, and CI comparing against it |
| `UX-427` | CI printing this run's timings, so a refresh is a copy |
| `UX-441` | that document moved into the `ci-reference-candidate` artifact |

The tool's own advice, on the run that reports drift, is

> re-record with `--record` and commit, which is how the reference stays
> true rather than becoming an alarm nobody reads

and `--record` on a contributor's own machine writes **that machine's**
seconds, which `UX-418` established cannot be compared to CI's in any
form. The numbers the advice asks for exist only in the artifact.

`git grep 'ci-reference-candidate' -- docs .claude` returns nothing
outside the two task files. `docs/contributing/fixing-guide.md` §6 maps
`tests/ci_reference.json` as "one CI run's per-file seconds, so drift is
CI against CI (`UX-420`)" and stops there. The `verify` skill's §3
describes the gate and `UX-442`'s two-run rule, and not the refresh.

So the route is: read the red step, download the artifact from that
run, replace the file, commit — four steps, written down nowhere.

## Required Fix

- **The four steps, where a contributor meets the red** — the `verify`
  skill's §3 is the likeliest home, since that is what a session reads
  before marking anything done.
- **The tool's own advice names the artifact**, or names the document
  that does. `--record`'s help text and the `--against` failure message
  both say "re-record with `--record`" without saying from what.
- **A guard that the two agree**: the artifact's name appears in
  `ci.yml` and in whichever document describes the route, so a rename
  cannot leave the instructions pointing at nothing.

## Out of Scope

- **`UX-442`'s two-run rule**: documented in the `verify` skill when it
  landed. This is about the refresh, not the gate.
- **Making the reference refresh itself**: a bot committing timings is
  a different decision and needs its own argument.

## Acceptance Test

A contributor following only committed documents can go from a red
drift step to a committed refreshed reference. A mutation renaming the
artifact in `ci.yml` and not in the document must redden the guard.

## Outcome (round 71, 2026-08-31) — 🟢 Done

### The gap

The tool told a contributor to re-record and not from what, and
`--record` on their own machine writes the wrong clock:

```console
$ git grep 'ci-reference-candidate' -- docs .claude
(nothing outside the two task files)
```

Four messages said "`--record`". None named the artifact. The artifact's
name lived in one `name:` field of `ci.yml` and nowhere a person would
look.

### The four steps, where a session meets the red

The `verify` skill's §3, because that is what is read before anything
is marked done: open the red `test (3.11)` job, download its
**`ci-reference-candidate`** artifact, replace `tests/ci_reference.json`
with it, commit it beside the change that made the file slower.

And the shape this repository has actually used more often, written
down for the first time: the gate prints `N.Ns` for the file it is
complaining about, and that figure **divided by the run's printed
shift** is the row to append - divided, because `expected = known x
shift` is the arithmetic the gate does and a raw append bakes that
run's slowness in as permanent slack. Six appends were made that way
across rounds 67-71 and every one is recorded in
`tests/ci_reference.json`'s own `note`; none of them was described
anywhere a contributor would find.

The section closes with what **not** to do, because the messages used
to invite it: `--record` locally replaces 380 files of CI's clock with
380 of yours and the gate goes quiet for the wrong reason.

### One name, three places, held equal

`CI_CANDIDATE_ARTIFACT` in `tools/dev_tier_drift.py`. Every message
interpolates it, `ci.yml` uploads under it, and the skill names it.
`test_the_refresh_route_is_written_down.py` asserts the three agree -
reading `ci.yml`'s `name:` **field** rather than searching the file, so
a comment carrying the old name cannot keep it green through a rename.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| F1 | `ci.yml` renames the artifact and nothing else | `test_the_workflow_uploads_the_artifact_the_tool_names` (1 failed, 3 passed) |
| F2 | the skill stops naming the artifact | `test_the_document_names_the_same_artifact` (1 failed, 3 passed) |
| F3 | the skill drops the do-not-record-locally warning | `test_the_document_says_not_to_record_locally` (1 failed, 3 passed) |
| F4 | one printed message goes back to bare `--record` | `test_the_tool_says_where_from_wherever_it_says_re_record` (1 failed, 3 passed) |
| F5 | the written reference's own `note` goes back to bare `--record` | the same clause (1 failed, 3 passed) |

### The guard that did not discriminate, and what it was doing wrong

**F4 passed against the first version of that clause**, and the reason
is this repository's own recurring defect one level up. The clause read
±400 characters around each line mentioning `--record` and asked
whether `CI_CANDIDATE_ARTIFACT` appeared anywhere in that window - so
the *neighbouring* message's mention satisfied it, and a message that
had lost its own could not be seen.

Rewritten to parse: the unit is the expression node, and a string that
says `--record` and the name that says from where have to be in the
**same** one. Which immediately found a fourth message the line scan
had also missed - the `note` written into `ci_reference.json` itself,
a dict value rather than a call argument, and the most likely place of
all for a contributor to meet the question. It said "Refresh with
tools/dev_tier_drift.py --record." and now says from where.

A window is a proxy for a statement. That is fixing guide §5, in a
guard written for an item about instructions pointing at nothing.

### Deviation from the Required Fix

- **None** on the three bullets. The `verify` skill's §3 is the home,
  as the item predicted; the tool's own advice names the artifact at
  all four sites; the guard holds the workflow, the tool and the
  document to one name.
- `docs/contributing/fixing-guide.md` §6's one-line map entry gained
  the route as well, since §6 is where a session looks up what a file
  is for.

### The suite

```console
$ make lint
All checks passed!

$ make test
5490 passed, 28 skipped, 1 warning in 290.72s (0:04:50)
```
