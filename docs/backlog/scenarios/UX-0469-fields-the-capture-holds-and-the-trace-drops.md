# UX-469: the resource a task held reaches no Perfetto carrier

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-466` measured it; nothing blocks the fix | **Found by:** round 72, `tools/dev_trace_coverage.py` over a generated two-plane capture | **Serves:** the reader who opens the trace to ask which tasks were waiting on DOWNLOAD and cannot filter for them | **Topic:** contracts

## Motivation

`UX-466`'s census reads a capture's own JSON and the bytes
`bga timeline` writes. Over a generated build with both a FETCH and a
BUILD queue:

```text
Plane 1: 4 reached, 6 dropped, 56 unassessable
    DROPPED   trace.spans[].primary_resource  (0/2 value(s) in the trace)
    DROPPED   trace.spans[].resources[]       (0/2 value(s) in the trace)
    DROPPED   graph.elements[].cache_key      (0/9 value(s) in the trace)
    DROPPED   run-context.pipeline_overhead[].phase (0/4 value(s))
```

The resource a task held — `PROCESS` or `DOWNLOAD` — is in every span
and reaches no slice, category, annotation or track. The carrier is
already there and already used for something else: slices carry
categories `bst-builder` and `bst-invocation`, so a reader can filter
by *which plane* a slice came from and not by *what it was waiting
for*, which is the question `wait-category` is the whole finding
about.

No committed capture could have shown this. `with_timeline`'s spans
carry one resource value, so the field is single-valued and the census
correctly calls it unassessable rather than dropped. It took a build
with two queues to make the question answerable, which is `UX-465`'s
argument in one line.

Two more in the same class, from the same census:

- `graph.elements[].cache_key` — a reader looking at a slice cannot
  tell which artifact it produced.
- Plane 2's static census *binary* lists (`static_executables`,
  `own_static`, `staged_by_dependencies`) — every per-element key
  arrives, no list of program names does.

## Required Fix

For each of the four, decide and record: a carrier, or a declared
reason it has none. `UX-466`'s census is the check — a field that gets
a carrier moves from `DROPPED` to `reached` in its output, and a field
that gets a reason moves into the tool's own declared list beside
`build-failed`'s.

Not "add everything": a trace with an annotation per field is a trace
nobody can read, and `UX-360`'s volume budget applies to the trace as
much as to the page. The resource is the one with a reader waiting for
it; the other three may well be declined.

## Out of Scope

- `trace.spans[].task_key`, which the census reports dropped because
  the trace **decomposes** it — the uid is the slice name and the rest
  is elsewhere. That is correct behaviour and `UX-466`'s docstring
  declares it.
- The third instrument `UX-470` asks for: this row is about fields the
  capture *holds*, not about fields the planes could hold and do not.
- Changing what any plane records — every field here is one the
  capture already holds, so the whole question is which carrier
  it should arrive in. A plane that could record more and does
  not is `UX-470`.

## Acceptance Test

```bash
python3 tools/dev_trace_coverage.py <a capture with two queues>
```

with `trace.spans[].primary_resource` and `trace.spans[].resources[]`
either under `reached` or named in the tool's declared list, and the
Perfetto query library gaining the question the new carrier answers.

## Outcome (round 73, 2026-09-01) — 🟢 Done

### The gap, measured

A two-queue capture, built from `tests/fixtures/specs/planted-serial-chain.json`
with `XDG_CACHE_HOME=/tmp/ux469cache`, snapshot at
`/tmp/ux469/.bga/runs/20260901T161438Z`:

```text
Plane 1: 4 reached, 6 dropped, 56 unassessable
    DROPPED   trace.spans[].primary_resource  (0/2 value(s) in the trace)
    DROPPED   trace.spans[].resources[]  (0/2 value(s) in the trace)
```

and what the two fields actually hold on that capture:

```text
primary_resource: Counter({'DOWNLOAD': 9, 'PROCESS': 9})
resources:        Counter({('DOWNLOAD',): 9, ('PROCESS',): 9})
```

Every span's list is the one-element list holding exactly its
`primary_resource`. That measurement is the basis of the decision
below: one of the two carries information, the other repeats it.

### After

```text
python3 tools/dev_trace_coverage.py /tmp/ux469/.bga/runs/20260901T161438Z

Plane 1: 5 reached, 3 dropped, 2 declined, 56 unassessable
    DROPPED   run-context.pipeline_overhead[].phase  (0/4 value(s) in the trace)
    DROPPED   run-context.producer.contracts[]  (0/21 value(s) in the trace)
    DROPPED   trace.spans[].task_key  (0/18 value(s) in the trace)
    declined  graph.elements[].cache_key
    declined  trace.spans[].resources[]
    reached   trace.spans[].primary_resource  (2/2 value(s) in the trace)

Plane 2: 17 reached, 0 dropped, 4 declined, 113 unassessable
    declined  plane2.static_census.per_element.{}.own_static[]
    declined  plane2.static_census.per_element.{}.staged_by_dependencies.runtime.bst[]
    declined  plane2.static_census.per_element.{}.static_executables[]
    declined  plane2.static_census.static_executables[]
```

All four fields the item named are settled: one carried, three
declined with a reason. Plane 2 has nothing dropped left.

And the question the carrier answers, run against a real trace with
Perfetto's own reader (`trace_processor_shell v57.2`):

```text
python3 tools/dev_perfetto_queries.py /tmp/ux469/two.pftrace --fetch
  resource-queues      Plane 1          2 row(s)
empty:  3/17  ['failed-processes', 'cpu-versus-wall', 'waited-on-flow']
errors: 0/17  []
```

```text
"resource","tasks","elements","seconds","window_seconds","mean_in_flight"
"PROCESS",9,9,8.938000,8.938000,1.000000
"DOWNLOAD",9,9,0.000000,0.000000,"[NULL]"
```

`mean_in_flight` 1.000 on a build whose `PROCESS` capacity is above 1
is the answer a reader came for, and `attribution.resource_wait_us`
cannot state it. `DOWNLOAD`'s window is zero — nine cached fetches
that took no measurable time — so the `nullif` on the divisor was
exercised for real rather than defensively.

### The decision, per field

- **`trace.spans[].primary_resource` — a carrier.** A `debug.resource`
  annotation on the Plane 1 slice, keyed on `(element uid, task kind)`
  because the resource is a fact about the *task*: `lib0.bst`'s fetch
  held `DOWNLOAD` and its build held `PROCESS`.
- **`trace.spans[].resources[]` — declined**, on the measurement
  above: a second annotation costing a key on every slice to carry
  values the first already carries.
- **`graph.elements[].cache_key` — declined.** A cache key is only
  meaningful against another run's, and one trace holds one run.
- **The Plane 2 static-binary lists — declined.** They name the
  programs the hook cannot see, which is the set with no slice to hang
  them on; the *conclusion* already reaches the trace as
  `elements_at_risk` and the per-element keys.

`DECLINED` in `tools/dev_trace_coverage.py` is where the three live,
the same shape as `dev_finding_coverage.UNREACHABLE`, and the census
reports them under their own verdict so "nothing carries this" and
"nothing carries this on purpose" stop looking alike.

### Mutations verified red and reverted (7)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| M1 | `task_resources` keeps the tuple key and *also* keys on the uid; the annotation reads the uid | 1 of 31 — `test_the_slice_carries_the_queue_the_task_held` (the slice read `DOWNLOAD`) |
| M1b | keyed on the uid alone | 2 of 31 — the above plus `test_the_queue_is_the_tasks_and_not_the_elements` |
| M2 | the call site never passes `resources=` to `_write_trackevent` | 2 of 31 — `test_every_documented_key_is_emitted` and the carry clause |
| M3 | the question scopes to `*native-process*` instead of `*bst-builder*` | 1 of 15 — `test_every_key_is_carried_by_the_plane_the_question_scopes_to` |
| M4 | the dictionary row for `resource` deleted | 2 of 46 — `test_the_dictionary_exists_and_documents_every_emitted_key`, `test_every_key_says_which_plane_it_rides` |
| M5 | `coverage()` never consults `DECLINED` | 1 of 17 — `test_a_declined_field_is_never_reached_or_dropped` |
| M6 | a declared path renamed (`cache_key` → `cacheKey`) | 1 of 17 — `test_the_declared_paths_are_paths_a_capture_really_holds` |

Each mutation was proved to have landed with a `grep -c` before the
run, and reverted from a copy after it.

### What the guards found, that the item did not ask for

- **`test_every_library_query_is_reachable_from_a_finding`** (`UX-368`)
  refused the new question until a finding pointed at it. It is right
  to: a query no finding opens is a query nobody finds. So
  `wait-category` and `capacity-recommendation` lead with
  `resource-queues` and keep `stalls` as the alternative — the finding
  names the largest wait category and the recommendation names a
  number to raise, and neither could say which queue.
- **The boundary guard's `PER_PROCESS` pattern** encoded "needs the
  trace" as "reads something per process". `debug.resource` is per
  *task* and still only in the trace, so the constant is
  `ONLY_THE_TRACE` now and the comment says why this one Plane 1 entry
  is not an exception.
- **`tests/fixtures/with_timeline/analyze.json`** was found four
  findings stale — `mesh-graph` where the analyzer now says
  `chain-graph`, and three of round 73's findings absent. Only
  `wait-category`'s `trace_query` was corrected here, because that is
  the field this item changed; the drift is `UX-486`.

### The export moved, measured

```text
page            291,588 -> 293,702   (+2,114, source)
golden          405,037 -> 407,265   (data 113,449 -> 113,563)
macro_micro     454,942 -> 457,284   (data 163,354 -> 163,582)
```

The source is the question, its `returns` table and the note above it;
the 114 B of payload is `resource-queues` joining two findings'
`trace_queries`. `golden`'s bound moved 406,000 → 411,000 with the
figures in the note beside it; `macro_micro`'s is not tripped and is
left, with its real 716 B of headroom recorded.

### Deviation from the Required Fix

- **None on the four fields.** One got a carrier and three got a
  declared reason, which is what the item asked for.
- One thing the item's Acceptance Test cannot see, recorded rather
  than left: `trace.spans[].resources[]` reads `reached` in the census
  the moment `primary_resource` has a carrier, because the census
  matches *values* and the two hold the same strings. The `DECLINED`
  entry is what keeps that honest; the instrument's inability to tell
  a carried value from a borrowed one is filed as `UX-485`.

### The runs

```text
make test-touching   905 passed, 19 skipped in 77.01s
make test            5,642 passed, 27 skipped in 318.54s (0:05:18)
make lint            ruff + PyMarkdown, both clean
```
