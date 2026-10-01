# UX-1180: values and console: a zero-length ratio, an epoch as hours, a tooltip-only explanation, a spaced hyphen, seven warnings

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer, bga/cli.py, bga/structural | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_value_is_what_it_names.py`, `tests/unit/test_the_console_stays_clean.py::test_no_number_renders_from_a_guess`

## Motivation

Page: the round-157 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `73af3af3`, Chromium 1440x900 and 390x844.

"Cores busy 983564.29×" (toolchain.bst, 0 ms duration, 938 ms CPU) and "172805.32×" (all.bst) in the element cards: a ratio over a zero-length span. macro_micro occupancy and run_instance print the epoch start as "496481.0 h", a point in time as a duration. A threshold box holding "abc" sets `aria-invalid=true` and explains itself only in the `title` tooltip ("\"abc\" is not a threshold this column can read, so no filter is applied"). `bga/cli.py:1416` prints a spaced hyphen and "1.5s" in the marginal gate message (the `UX-1172` survey read reader text and the CPU-floor line, not this one). The two-plane page logs 7 console warnings "has no bga:quantity; guessed" (direct_count, blast_count, building_count, assembling_count, measured_us, element_count x2) and the console-clean guard reads golden only.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A zero-length span has no cores-busy ratio; a timestamp is not printed as a duration; an unreadable threshold says so on the page; the gate message has no spaced hyphen and a spaced unit; the two-plane page logs no quantity warning and the console guard reads it.

## Out of Scope

The schema's quantity vocabulary beyond the seven named keys.

## Acceptance Test

On the two-plane page no element card reads a cores-busy ratio over a 0 ms span, no duration cell is an epoch, an unreadable threshold shows text on the page, `cli.py`'s gate message reads "1.5 s" without a spaced hyphen, and the console guard reads the two-plane page with 0 warnings. Mutation: restore one defect, and the guard reds.

## Decision

### Architect's section (round 158)

```text
Route:     `correlate.py` publishes no `cores_busy` for an element whose Plane 1 duration is 0 or whose ratio exceeds the host's cores (a ratio over no span is not a measurement); the epoch start keys declare a timestamp `bga:quantity` so `format.js` renders an instant; the seven keys declare their quantity in the schema; `cli.py`'s gate message reads "1.5 s" with no spaced hyphen; the console guard boots the two-plane page.
Rejected:  hide the ratio in the card - the payload would still carry 983564.29 to every other consumer; silence `quantityFor`'s warning - it is the instrument, and the schema gap is the defect.
Files:     bga/correlate.py (~375, the `cores_busy` assignment); bga/schemas.py (bga:quantity for blast_count, building_count, assembling_count, measured_us, element_count; the epoch start keys of occupancy and run_instance); bga/viewer/format.js (`quantityFor`'s formatter only if a timestamp quantity is not already rendered); bga/cli.py (~1413-1416); tests/unit/test_the_console_stays_clean.py (`observed`: a seventh boot, `pages.two_plane_run`); tests/unit/test_a_value_is_what_it_names.py (new); tests/tiers.py.
Guard:     test_the_console_stays_clean.py::test_no_number_renders_from_a_guess reads the two-plane page with 0 warnings; test_a_value_is_what_it_names.py - no card reads a cores-busy ratio over a 0 ms span, no duration cell renders an epoch, the gate message matches "1.5 s" and holds no " - ".
Mutation:  remove `blast_count`'s bga:quantity; the console guard reds on the two-plane boot.
Class:     product
Split:     C5, one track, parallel. The "unreadable threshold shows on the page" clause moves to UX-1191 (B): that row replaces the per-column threshold box with one filter grammar, so the message belongs to the grammar's parse error; this row's Files leave `interrogable` alone. `direct_count`'s quantity is declared by C1 (it sits in the `fan_in` block C1 extends).
Question:  none
```

Budgets: bytes ~+0 on the page half (producers and schema); controls 0; height 0; words ~+2 (an instant reads longer than "496481.0 h").
Overlap: bga/schemas.py with C1 (different blocks, except `direct_count`, handed to C1); the threshold clause with UX-1191.

### Where the route was wrong

```text
1. A `timestamp` quantity is not addable: `test_one_unit_per_dimension` refuses a second member of
   the time dimension and refuses a `_us` key declared anything but `duration_us`. Taken instead: a
   hint `bga:instant: true` beside `bga:quantity: duration_us` on `started_at_us`, `horizon_start_us`,
   `horizon_end_us`; format.js `quantityFor` returns `instant_us`, which renders a UTC date from
   1e15 us (2001) up and a duration below it - a run's zero-based offset stays a duration.
2. `blast_count`..`measured_us` and `element_count` are declared on `_BLAST_HINTS` (the blast
   document), not on the analyze page's `resource_blast` rows; the warnings came from the latter.
   `_BLAST_COUNTS` is now the one declaration, spread into both; the rows carry the quantity only
   (the descriptions stay on the blast document) to keep the page bytes down.
3. The zero-length span is Plane 2's own `wall_span_s` (9.5e-7 s), not Plane 1's duration: `correlate`
   publishes no `cores_busy` under 1 ms, the resolution the page prints. No host-core ceiling: the
   capture here carries no `host_cpu_count`.
4. `direct_count` is already declared under `fan_in`; the warning came from the rows, so C1 is not
   needed for the console guard.
5. The second gate line ("not a pass - it is an empty check") had the same spaced hyphen; fixed.
```

## Outcome

**The gap measured** (`gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, plus `capture report`; `macro_micro`; Chromium 1440x900, before the change):

```text
console "has no bga:quantity; guessed"   6 distinct keys, 7 warnings (assembling_count, blast_count,
                                          building_count, direct_count, measured_us, element_count x2);
                                          all from resource_blast.rows[] and duration_resolution
toolchain.bst / all.bst card              Cores busy 983564.29x / 172805.32x (wall_span_s 9.5e-7 / 1.2e-6 s)
macro_micro                               "496481.0 h" x3 (horizon_start_us, horizon_end_us, started_at_us)
cli.py gate line                          "8.0s of the 8.0s ... ) - on the path"
```

**The close measured** (same fixtures, after):

```text
console guard, 8 boots (two-plane added)  0 "has no bga:quantity" warnings; 9 passed in 13.6 s
toolchain.bst / all.bst cards             no Cores busy row (Duration 0 ms)
macro_micro                               0 epoch-as-hours; "Started at, since the epoch" reads a UTC date
gate line                                 "8.0 s of the 8.0 s this change added ... (stretch 1.00 > 0.50); on the path"
page bytes (export, uncompressed)         golden 315,642 -> 316,085 (+443), macro_micro 376,633 -> 377,054 (+421)
xl_both controls / height                 0 / 0 (no control, no row)
new guard                                 tests/unit/test_a_value_is_what_it_names.py, 4 passed in 11.6 s (MEDIUM)
```

**Mutation table** (each restored from a copy; `PYTEST_XDIST=`):

| Mutation | Reddened | Count |
|---|---|---|
| `blast_count` loses its `bga:quantity` | `test_the_console_stays_clean.py::test_no_number_renders_from_a_guess` | 1 failed |
| `correlate.py` publishes `cores_busy` whatever the span | `TestNoRatioOverNoSpan` (`['all.bst', 'toolchain.bst'] == []`) | 1 failed |
| `INSTANT` dropped from `hintsOf`'s list | `TestAnInstantIsNotADuration` | 1 failed |
| gate line `1.0 s` back to `1.0s` | `TestTheGateMessageIsSpaced` | 1 failed |
| gate line `; ` back to ` - ` | `TestTheGateMessageIsSpaced` | 1 failed |

**Deviation.** The unreadable-threshold clause moves to UX-1191 (architect's split); the row's Acceptance Test line "an unreadable threshold shows text on the page" is left to it. The Decision's route 1 replaces the architect's timestamp quantity with `bga:instant`. `tests/tiers.py` carries the new file's MEDIUM row because the brief asked for it; `test_the_console_stays_clean.py` gained an eighth boot (2 -> 4 runs, prose updated).

