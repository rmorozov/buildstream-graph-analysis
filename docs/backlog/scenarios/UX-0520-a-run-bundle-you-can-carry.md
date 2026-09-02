# UX-520: a capture you can carry to another machine in one command

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-381` (the capture-directory contract this bundles), `UX-186` (the host manifest that must travel with it), `UX-300` (what the raw log weighs) | **Found by:** round 77, field request — *"convenience commands for bga snapshot export and load, to create a run bundle and move it to another machine for later analysis"* | **Serves:** the engineer who captured on a build runner and wants to read it on a laptop | **Topic:** store

## Motivation

The analysis half already works. A run directory copied out of its store,
to an unrelated path, on no project, analysed from an unrelated working
directory:

```console
$ cp -r tests/fixtures/golden/mixed_task_kinds /tmp/.../moved/run
$ cd /tmp && bga analyze /tmp/.../moved/run
Build Efficiency Report
Run: golden-fixture-manifest-hash-v1
Instance: /tmp/.../moved/run
$ echo $?
0
```

So this is not a portability defect. What is missing is that **`run/` is
not the capture**. `UX-381` made the layout a stated contract, and half
of what a reader needs sits *beside* `run/`, not inside it:

```text
.bga/runs/<stamp>/run/            graph.json, trace.json, run-context.json, sources.json
.bga/runs/<stamp>/plane2.json     the Plane 2 report          conditional
.bga/runs/<stamp>/plane2.log.gz   the raw per-process trace   conditional
.bga/runs/<stamp>/plane2-resource.json                        conditional
.bga/runs/<stamp>/host-samples.jsonl                          conditional
.bga/runs/<stamp>/analyze.json                                conditional
.bga/runs/<stamp>/build.log, element-slice.json, capture-context.txt
```

A user who tars `run/` — the directory every command's help names — takes
Plane 1 and leaves Plane 2 behind. The tool then says so rather than
lying (`plane2_absence` is a published key), which is why this is a
convenience row and not a correctness one; but "it told you afterwards"
is a poor substitute for a command that packs the right set.

The contract also decides what `load` must refuse: each member carries a
version (`graph/v9`, `trace/v9`, `run-context/v9`, `plane2/v3`,
`sources/v1`, `analyze/v4`, `host-samples/v1`), so a bundle from a newer
`bga` is a thing the receiving side can recognise instead of half-read.

**The cross-host question answers itself, and that is the point.**
`UX-186`'s host manifest lives in `run-context.json`, so it travels
inside the bundle: a capture carried from a runner to a laptop keeps the
evidence that it was measured elsewhere, and `bga compare` on the far
machine caps confidence and refuses exactly as it would at home. A bundle
format that dropped or rewrote the manifest would turn `UX-186`'s
refusal off by accident, which is the one way this row could do harm.

## Required Fix

- `bga snapshot --export <stamp> [-o FILE]` writes one archive holding
  the capture-layout members that exist for that snapshot, plus a
  manifest naming each member's contract version and the `bga` revision
  that packed it.
- `bga snapshot --load FILE` unpacks into this project's store under the
  bundle's own stamp — the stamp is the capture's identity, so it is
  preserved, not reassigned — and refuses rather than half-loads when a
  member's contract version is one this `bga` does not read, or when the
  stamp is already present and its contents differ.
- The raw Plane 2 log is the bundle's largest member by far and is only
  needed to re-fold the report. Whether it ships by default is a
  decision the row must make and state, with the sizes measured on a
  real capture rather than assumed.
- The two commands round-trip: export, load into an empty store, and
  `bga analyze` on both sides prints the same report.

## Out of Scope

- Publishing to a git ref, which is `UX-81`'s capture-ref scheme and
  already exists for the CI direction. This is the local, ad-hoc
  direction: one file, `scp`, done.
- Normalising durations across hosts. `UX-186` and `UX-129` both refuse
  that deliberately, and a bundle that made two machines comparable
  would be the model-dressed-as-measurement those rows exist to stop.
- Bundling more than one snapshot. A set of runs is `bga baseline`'s
  question and it has an answer.

## Acceptance Test

A capture exported, the store deleted, the bundle loaded into an empty
project, and `bga analyze @last` printing byte-identical output to the
pre-export run — pasted both sides. Mutation: drop `plane2.json` from
the archive — the loaded capture's report must say Plane 2 is absent
rather than reporting as if it never had one.

## Outcome

_Not started._
