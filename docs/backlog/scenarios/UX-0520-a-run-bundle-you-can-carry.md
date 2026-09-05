# UX-520: a capture you can carry to another machine in one command

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-381` (the capture-directory contract this bundles), `UX-186` (the host manifest that must travel with it), `UX-300` (what the raw log weighs) | **Found by:** round 77, field request — *"convenience commands for bga snapshot export and load, to create a run bundle and move it to another machine for later analysis"* | **Serves:** the engineer who captured on a build runner and wants to read it on a laptop | **Topic:** store | **Area:** bga

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
- **Everything ships by default**, and a switch excludes the Plane 2
  capture for the reader who wants a small bundle. Decided by the
  requester rather than derived: a bundle that silently dropped a
  member would make the far machine's report quieter than the near
  one's, and "why is Plane 2 missing over there" is a worse question
  than a large file. The switch's own output says what it left out, and
  the bundle's manifest records the omission so `load` can say so too.
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

## Outcome (round 80, 2026-09-02) — 🟢 Done

`bga bundle --export STAMP [-o FILE] [--no-plane2]` and `bga bundle
--load FILE`, with `bga/bundle.py` deriving its member list from
`UX-381`'s `CAPTURE_LAYOUT` rather than restating it.

**Deviation, and it is the first thing to read.** The Required Fix spells
this `bga snapshot --export/--load`. `bga snapshot` dispatches to
`tools/bga_snapshot.py`, which this round's track was forbidden to touch,
so the commands landed as a new native subcommand instead. Same
behaviour, different spelling; the task file's two invocations above are
the ones that exist.

**The gap, measured.** A `tar` of `run/` carries 3 of the 7 members a
capture holds:

```console
$ bga bundle --export @last -o run.tar.gz
Wrote run.tar.gz
  snapshot 20260902T101112Z: 7 member(s), 56.3K before compression
```

Four of those seven — `plane2.json`, `host-samples.jsonl`, `build.log`,
`capture-context.txt` — sit beside `run/` and are what `run/`-tarring
loses.

**The close, measured.** Exported from one project, loaded into an empty
one, `bga analyze @last` both sides: 136 lines each, and `diff` reports
7 differing lines, every one of them the store's absolute path (the
`Plane 2:` line, the `Instance:` line, and five next-step command lines).
Every number is identical. Byte-identical is not achievable across two
paths and never was — the Motivation's own paste shows the instance path
changing — so the claim is "identical after substituting the project
root", pasted both ways in the track report.

The acceptance mutation: exported with `--no-plane2`, loaded, and the
far report says `Plane 2 was not captured for this run, so there is no
per-process detail.` rather than reporting as if it never had one.

**Found and filed.** `readable_contracts()` was
`contracts.ids() | superseded()`, and the first real bundle of a healthy
capture was **refused** for carrying `graph/v9`, `trace/v9` and
`run-context/v9` — *input* shapes no `bga` module stamps, so in neither
set. Worked around here by unioning the contracts `CAPTURE_LAYOUT` names;
the registry gap itself is `UX-540`.

**Mutation table** (`tests/unit/test_a_run_bundle_you_can_carry.py`,
19 clauses, 19 passed baseline):

| mutation | reddened | count |
|---|---|---|
| pack only `run/` | `every_layout_member_that_exists_travels` +4 | 5 failed, 14 passed |
| carry the `DERIVED` members | `derived_members_do_not_travel` +1 | 2 failed, 17 passed |
| manifest forgets the contract | `manifest_names_each_members_contract_version` | 1 failed, 18 passed |
| readable set drops the layout union | `a_fresh_capture_is_not_refused_by_its_own_bga` +9 | 10 failed, 9 passed |
| `--no-plane2` also drops host samples | `no_plane2_drops_the_plane2_members_and_records_it` | 1 failed, 18 passed |
| everything excluded by default | `everything_ships_by_default` +3 | 4 failed, 15 passed |
| no manifest-schema refusal | `a_newer_bundle_format_is_refused_by_name` +1 | 2 failed, 17 passed |
| no unknown-contract refusal | `a_member_contract_this_bga_cannot_read_is_refused` | 1 failed, 18 passed |
| unpack first, refuse after | the two "nothing written" clauses +1 | 3 failed, 16 passed |
| drop the prefix clause | `an_entry_outside_the_member_prefix_is_refused_as_such` | 1 failed, 18 passed |
| drop the `isfile` clause | `a_directory_entry_under_the_prefix_is_refused` | 1 failed, 18 passed |
| drop the `..` clause | `a_declared_member_that_escapes_the_directory_is_refused` | 1 failed, 18 passed |
| archive/manifest agreement unchecked | `a_manifest_naming_a_member_the_archive_lacks_is_refused` | 1 failed, 18 passed |
| reassign the stamp | `the_stamp_is_preserved_rather_than_reassigned` +6 | 7 failed, 12 passed |
| no differing-contents refusal | `a_different_capture_under_the_same_stamp_is_refused` | 1 failed, 18 passed |
| refuse any present stamp | `the_same_bundle_loads_twice_without_complaint` +1 | 2 failed, 17 passed |
| rewrite run-context on load | `the_host_manifest_arrives_byte_identical` +1 | 2 failed, 17 passed |
| refused bundle exits 0 | `a_refused_bundle_exits_two_and_says_why` | 1 failed, 18 passed |

One guard did not discriminate on the first pass: a single traversal
clause whose escaping entry was already caught by the manifest-membership
check below it — `if False:` over the prefix check left all 17 green. Split
into three clauses with three tests asserting the specific refusal, each
mutated red separately. `return 2` -> `return 0` is same-length and left a
stale `.pyc` after restore (`UX-508`); cleared and re-confirmed green.
