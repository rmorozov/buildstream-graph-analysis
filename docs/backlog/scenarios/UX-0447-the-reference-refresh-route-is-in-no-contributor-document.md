# UX-447: the reference-refresh route is in no contributor document

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** review 8, checklist item 4 | **Serves:** the contributor whose PR the drift gate stops, who is told to re-record and not where from | **Topic:** docs

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

## Outcome

_Not started._
