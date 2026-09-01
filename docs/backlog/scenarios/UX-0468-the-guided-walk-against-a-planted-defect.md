# UX-468: no walk of the guides has ever started from a defect somebody planted

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-465` stages 1–2 and 4 (a project whose defect is a parameter) · reads `UX-467`'s answer key | **Found by:** round 72, thread 3 of the audit — whether the README and guides flow really lets you spot a real build efficiency problem | **Serves:** the reader who follows the front door end to end and arrives somewhere other than the problem | **Topic:** docs

## Motivation

Rounds 58, 60 and 69 each walked `bga snapshot → bga view → Perfetto`
and filed what they found. Every one of those walks started from a
project and asked what the tool said about it. None started from a
**defect chosen in advance** and asked whether the flow leads to it.

Those are different questions. A walk that starts from the output
grades the output's plausibility; only a walk with a planted answer can
report a miss. And a miss is the failure mode the guides actually have
— `UX-246` found the journey guide never reached what-if, and
`UX-281` found the satellite pages were dead ends, both of which a
plausibility walk had passed over.

`UX-465` stage 4 makes the defect a parameter of the generated
project, which is what turns this from an anecdote into a repeatable
measurement.

## Required Fix

For each of three planted defects — one per reader whose coverage
`UX-463` measured as thin (local-optimizer, recipe-author,
graph-owner):

1. Generate the project with the defect, capture it, and record the
   **exact click and command path** from `README.md` to the sentence
   that names the defect: every document opened, every command run,
   every page section visited, and the count.
2. Record where the path breaks: a guide that does not link onward, a
   page that shows the number without the sentence, a Perfetto query
   that needs an element name the page never offered.
3. One row per break, filed before the walk's own commit lands
   (fixing guide §3.11).

The deliverable is the recorded walk, in `docs/audits/`, with the
counts — not a list of impressions.

## Out of Scope

- Fixing the breaks. They get rows; a walk that both finds and fixes
  is a walk whose findings nobody can check.
- Rewriting the guides wholesale. `UX-231`'s rule — every direction
  names its reader — already governs their shape.
- Readers whose coverage is already complete. The capacity-operator's
  two findings are both produced by a committed capture, and a fourth
  walk for it is spend without a gap behind it.

## Acceptance Test

A document under `docs/audits/` naming, per defect, the number of
documents opened and commands run before the tool named the defect,
and the breaks found — with each break carrying its filed row id.
