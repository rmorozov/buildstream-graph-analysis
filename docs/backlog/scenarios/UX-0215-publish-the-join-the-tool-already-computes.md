# UX-215: publish the join the tool already computes

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-201 (the schema vocabulary), UX-190 (outputs that say what shape they are), UX-051 (`bga correlate`)

## Motivation

`bga/correlate.py:141` assembles an `ElementJoin` per element:

```text
Plane 1   on_critical_path, critical_path_share,
          potential_saving_us, saving_share, blast_radius
Plane 2   cores_busy, cpu_coverage, requested_jobs,
          native_findings, unused_dependencies,
          dominant_binary, serial_binary, peak_rss_kb
```

`_plane2_view` (`correlate.py:277`) builds the Plane 2 half out of
`per_element_parallelism`, `cpu_time.per_element` and
`peak_memory.per_element` — every one of them already per element.

And then it stops half a step short. Measured on `main`:

```text
bga correlate --format json   emits the join: 11 rows on examples/06,
                              every field above present and correct
its `schema` key               absent — the payload is unversioned
bga correlate --schema         "correlate produces no versioned JSON output"
schemas.names()                ['analyze/v1','blast/v1','compare/v1','store/v1']
bga view payloads()            does not serve it
analyze/v1                     Plane 2 run-level only: plane2_coverage,
                               utilisation. No per-element parallelism,
                               CPU or memory.
```

So the tool's most valuable derived object — the one place where "this
element is on the path, is worth 12.05s, and was pinned to one job on
four cores" is a single row — is emitted as an **unversioned blob that
nothing can consume**. No `schema` stamp, so `UX-190`'s contract does
not cover it. No view-hints, so `bga view` could not render it
generically even if it were served. And it is not served. CI cannot
gate on it; no external consumer can validate it.

The round-24 review proposed building this as a new viewer feature and
separately as a new "three-plane investigation ladder". Both are this
one already-computed join, missing a contract — which is why the fix is
a stamp, a schema and some wiring rather than analysis.

This is `UX-206`'s pattern for the fourth time (after `blast_tree`,
`headline`, and the compare payload the band needed): the analysis
knows, and the published schema does not say.

## Required Fix

1. A `correlate/v1` document: the JSON `bga correlate --format json`
   already emits, stamped and validated like the other four, and
   `correlate --schema` answering instead of refusing. No new analysis,
   no renaming, no reshaping — if a field is wrong it is wrong today,
   and this round is not the place to find out.
2. `analyze --plane2` grows a per-element block in `analyze/v1` from
   the same function, so the *report* carries the join rather than
   requiring a second command. Additive, so no version bump.
3. `bga:columns` (v2), `bga:quantity` and `role: "element"` declared
   for it, so `UX-208`'s Inspect and `UX-205`'s thresholds work on it
   with no viewer change.
4. Absent Plane 2 is a **degrade, not an error**: the block carries the
   Plane 1 half and says the Plane 2 half is missing, in the shape
   `UX-156` established.

## Out of Scope

- Any new per-element measurement. If Plane 2 did not measure it, this
  does not invent it.
- The viewer work that consumes this (`UX-216`), and the ladder
  presentation (`UX-216`'s element section).
- Changing `bga correlate`'s text output.

## Acceptance Test

On `examples/06` with its Plane 2 report: `bga correlate --format json`
validates against `correlate/v1`, and every element in the text output
appears as a row with the same numbers (asserted field by field against
`format_correlation`'s own input, not re-derived). `bga analyze
--plane2 … --format json` carries the same per-element rows.

Mutations, each asserted red: drop `cores_busy` from the published row
→ the round-trip guard fails; publish an element Plane 2 named that
Plane 1 never declared (`declared: false`) and let it carry a
recommendation → the `UX-66` guard fails. Without `--plane2`, the block
is present, Plane-1-only, and says so — no error, no silent zeros.
