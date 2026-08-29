# UX-401: no key is terminal-only in silence

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-389 (the fourteen blocks it will hold in place) | **Serves:** whoever adds the sixteenth block | **Topic:** guards

## Motivation

`UX-389` counts the damage — fourteen of twenty-five Plane 2 blocks
reach no browser — and `UX-385`'s `commands_not_observed` became the
fifteenth *one round after being added*, which is the proof that this
is a treadmill, not a backlog item: every new capture-side block
defaults to terminal-only, silently. Fixing the fourteen (`UX-389`)
without a guard leaves the sixteenth to the next walk.

## Required Fix

A reachability census as a guard: enumerate the keys of every
document the page can be handed (the analyze payload and the plane2
per-element reductions are the two that leak), and assert each key is
either (a) rendered by some registered section — provable through the
chapters/section registry — or (b) declared terminal-only in one
table the guard reads, with a reason, the same declared-not-implied
shape as the skip census. An undeclared unreachable key is RED.

## Out of Scope

- Deciding which of the current fourteen should render — that triage
  is `UX-389`'s job; this guard freezes whatever `UX-389` decides.
- Perfetto-side reachability — the trace dictionary already declares
  what the trace carries, and `UX-395` covers the one drift found.

## Acceptance Test

- Falsification: add a synthetic key to a fixture payload with no
  section and no declaration — RED; declare it — GREEN; render it —
  GREEN with the declaration flagged stale (a declared key that a
  section renders is itself RED, so declarations cannot rot).

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The gap, measured

`UX-389` made every Plane 2 block declare a destination and
`test_every_plane2_block_has_a_destination.py` made the declaration
binding — but only as far as the *payload*:

```python
    def test_every_payload_destination_resolves(self, payload, report):
        ...
            if _resolve(payload, where) is None:
                unresolved.append(f"{block} -> {where}")
```

Resolving in the payload is not reaching a reader, and reaching a
reader is what the filing was about. Nothing asserted the other end,
and nothing censused the analyze document at all: `git grep` finds no
guard that reads a document's keys and the booted page's sections in
the same run.

### After

The census, over a two-plane run:

```text
analyze/v4 top-level keys         53
  drawn as their own section      46
  scalars, in the `Run` block      5
  declared DRAWN_ELSEWHERE         2
  declared TERMINAL_ONLY           0

plane2/v3 blocks with a destination  25
  join               3
  payload           14
  terminal           8
  written by this capture         24
```

Every key of the analyze document reaches a reader today, so the new
`TERMINAL_ONLY` slot is **empty** — and that emptiness is a clause, not
an omission: filling it reddens the clause that says so, which asks the
filler to name the round that decided it.

```text
$ PYTHONPATH=. python3 -m pytest \
    tests/unit/test_no_key_is_terminal_only_in_silence.py -q
.........
9 passed in 4.94s
```

### Four destinations, and silence is not one

The page already had three: a section of its own, a row of the `Run`
block (where `renderSummary` puts every scalar — which is why 5 of the
53 need no section and no entry), and a `DRAWN_ELSEWHERE` declaration.
`TERMINAL_ONLY` is the fourth, and it is the shape `bga/plane2.py`
already uses on the capture side: a key, and the reason it stops at
the terminal, at least twelve words of it.

The binding runs the other way too. Each `PAYLOAD` destination is
resolved against the *rendered document*: the section exists, and the
member's own label is inside it — so `plane2_coverage.process_count`
arriving in the payload is not enough; the section that carries it has
to name it. That is the claim `UX-389` could not make about the
fourteen it fixed.

### Mutations verified red and reverted (4)

Counts are what the run printed. Each was applied to the committed
tree and reverted with `git checkout` after the run.

| # | mutation | reddened |
|---|---|---|
| B1 | `render()` skips `plane2_coverage` the way it skips `schema` - `UX-389`'s defect, reintroduced in the one line that can cause it | `test_every_key_of_the_document_reaches_a_reader`, `test_every_payload_destination_is_drawn`, `test_every_carried_member_is_drawn_where_it_landed`; 3 failed, 6 passed |
| B2 | `provenance` declared `TERMINAL_ONLY` with a long enough reason, while the page still draws it | `test_nothing_declared_unreachable_is_drawn`, `test_the_slot_is_empty_because_nothing_needs_it`; 2 failed, 7 passed |
| B3 | a `TERMINAL_ONLY` entry whose reason is two words | `test_a_declaration_carries_a_reason`, `test_the_slot_is_empty_because_nothing_needs_it`; 2 failed, 7 passed |
| B4 | `coverage_additions` lands `process_count` under another name, so the block is declared to reach `plane2_coverage.process_count` and carries `traced_thing_tally` instead | `test_every_carried_member_is_drawn_where_it_landed`; 1 failed, 8 passed |

B2 is the filing's own third case - "a declared key that a section
renders is itself RED, so declarations cannot rot".

### A guard of my own that did not discriminate

B4 was run three times. The first two passed.

1. The first mutation renamed the destination *path* in
   `DESTINATIONS`. `coverage_additions` derives the carried member's
   name from that same path, so both sides moved together and the page
   drew the new name - the mutation renamed the expectation instead of
   breaking it. This is the shape `UX-392` and `UX-400` each hit once
   this round.
2. The second mutation renamed only the carry, which is a real
   divergence - and the clause still passed, because it looked for the
   member's *words* in the section's prose. The schema declares
   `process_count` whether or not a value arrives, so its description
   is in that prose either way: the clause was measuring the schema and
   reporting it as carriage.

The clause now reads `data-key` off the terms the page actually drew
(`UX-374` puts the published key on every one), which is the
difference between "the section mentions it" and "the section drew
it". Only then did B4 go red.

### Deviation from the Required Fix

- The Required Fix names "the analyze payload and the plane2
  per-element reductions" as the two documents that leak. The plane2
  per-element reductions reach the page as `element_join` rows, which
  `UX-356`'s guard already censuses field by field; rebuilding that
  here would be a second copy of one census, so this file asserts the
  cross-reference instead — a block declared to land on a join field
  lands on a population the page has a written destination for.
- `compare/v2` and `store/v1` are **not** censused. Both are optional
  documents the page draws two sections from, and a census over them
  needs a two-run store to boot against; that is its own instrument
  and its own cost, and this file says so rather than pretending the
  census is wider than it is.
