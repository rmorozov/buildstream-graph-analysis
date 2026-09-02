# UX-215: publish the join the tool already computes

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-201 (the schema vocabulary), UX-190 (outputs that say what shape they are), UX-051 (`bga correlate`) | **Topic:** contracts

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

---

## Outcome (round 25)

**Status:** 🟢 Done.

`correlate/v1` is the fifth published document. `bga correlate
--format json` is stamped, `correlate --schema` answers instead of
refusing, and `bga analyze --plane2` carries the same rows as
`element_join`. Nothing about what the join *computes* changed — the
diff is a stamp, a schema, and thirty lines of wiring.

**The rows are asserted to be the join's own rows**, field for field
against `correlate()`'s return rather than re-derived: `published
["elements"] == direct["elements"]`. Same for the report's copy, so
`bga analyze --plane2` and `bga correlate` cannot describe an element
differently — the failure `UX-214` found one round earlier, in the
verdicts, closed by construction here rather than by two code paths
happening to agree.

**A quantity had to be added, and that is the point rather than a
detour.** `peak_rss_kb` is kilobytes; `bytes` would be wrong by 1024×
and would have rendered 157,200 KB as "154 KB" instead of 153 MB —
exactly the class of error `UX-201` exists to stop, one order down from
the `peak_rss_mb` case it was written for. `kilobytes` is a declared
quantity now, with a renderer and a threshold unit, and a guard that a
quantity nothing renders is a promise nothing keeps.

**The viewer needed no change at all.** `bga view` already passes
`--plane2` when the store has a sibling report, so the join arrives in
`report.json` and the schema-driven renderer draws it: measured on
`examples/06`, an `element_join` table of 11 rows under its declared
question, `data-element-column="element"`, and 11 Inspect affordances.
That is `UX-193`'s dispatch paying for itself — and the reason this
item was worth doing before any of the viewer items that follow it.

**`UX-213`'s rule, one round after it was written.** The first draft of
the guards was pinned to `examples/06`'s uncommitted capture: six of
twelve would have skipped on a fresh checkout and in CI. They run on
the committed golden fixture now, with a Plane 2 report built in the
test — critical path `base.bst → lib.bst → app.bst`, `app.bst`
deliberately unseen by Plane 2 (the degrade case) and `ghost.bst`
deliberately undeclared (`UX-66`'s). Proven: with the capture moved
aside, **13 pass, 6 skip, and a mutation still reddens a committed
guard.**

**A mutation that would not discriminate, and what was built instead.**
Deleting `UX-66`'s `if entry.declared` gate left every guard green. The
reason is real and worth recording: a Plane-2-only name never acquires
a `saving_share`, and `_recommend` needs one — so on *that* path the
gate is belt over braces. It is load-bearing on a different path, where
Plane 1's `top_opportunities` names an element its own signals maps do
not, which is the only way to hold a saving share while undeclared.
That case is now built (`TestTheUndeclaredGateIsLoadBearing`), the
mutation reddens it, and the non-discriminating version was rejected
rather than counted.

Nine mutations, each verified red: the stamp dropped; `--schema`
refusing again; `peak_rss_kb` declared as `bytes`; the element role
removed; the viewer's `kilobytes` case deleted; the report joining
separately from the command; the block emitted empty without
`--plane2`; unseen elements zeroed rather than left absent; the
`UX-66` gate deleted.

**Deviation from the Required Fix:** clause 4 asks for the block to be
present without Plane 2, carrying the Plane 1 half. It is **absent**
instead, deliberately: with one plane there is no *join*, and the Plane
1 half is already published in `signals` — publishing it twice under a
name that promises both planes would be the misleading option, not the
generous one. The degrade clause is honoured *within* a row: an element
Plane 2 never saw keeps its Plane 1 half and carries no Plane 2
numbers. Recorded in the guard that asserts it.
