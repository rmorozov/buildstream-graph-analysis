# UX-329: the terminal and the viewer disagree about Plane 2

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-202 (plane2_coverage), UX-297 (the report beside the run) | **Serves:** R1, R2 | **Topic:** analysis

## Motivation

Stranger walk friction 15, against `bga view --help`'s own promise
that "the viewer and the terminal can never disagree about what a
run says": on a snapshot carrying `plane2.json`, `bga analyze
@last` publishes `plane2_coverage: null` and never mentions
Plane 2 exists — while `bga view @last` on the same alias serves
the same schema with `plane2_coverage` fully populated, because
the viewer auto-attaches the sibling file and `analyze` requires
`--plane2` and never hints at it (`correlate` auto-finds it too —
analyze is the odd one out). And the absence grammar conflates two
absences: `has_timeline: false` and the export's "no raw Plane 2
log, so there is no timeline to carry" read as "Plane 2 absent"
when the Plane 2 *report* is present and only the raw log was
dropped — a stranger cannot tell "not captured" from "captured,
log not kept".

## Required Fix

`analyze` auto-attaches the sibling `plane2.json` exactly as
`correlate` and the viewer do (one discovery function, three
callers), `--plane2` remaining the override; where the file exists
and is not attached (explicit `--no-plane2`?) the report says so.
The absence grammar splits: "Plane 2 not captured" vs "Plane 2
captured; raw log not kept (no timeline)" — one sentence pair,
used by the terminal, the page and the export (the UX-156
absence-is-stated rule, applied to the plane).

## Out of Scope

- Timeline regeneration from anything but the raw log (nothing
  can conjure it; the sentence just stops implying more).

## Acceptance Test

On the fixture with a plane2 sibling: `analyze` and `view` publish
identical `plane2_coverage` (byte equality — the help's promise
becomes a guard); on a run with report-but-no-raw-log the page and
terminal print the "captured; log not kept" sentence, on one with
neither the "not captured" sentence (both asserted; mutation:
collapse the two sentences → red).
