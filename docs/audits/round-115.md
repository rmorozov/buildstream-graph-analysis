# Round 115 — the owner's twelve points, a design review, and fifteen filings

Run on 2026-09-13.

The owner read the 0.4.1 page on their own project and brought twelve
considerations. This round challenged each against the tree and the
guide, ran the `design-review` skill on yesterday's all-planes walk
capture (3 elements, both planes and the spine, served and exported),
re-measured the volume claims on the 1,202-element synthetic export,
and filed what survived. No code moved; four styleguide sections did.

## The twelve, challenged

| # | the owner said | measured | verdict |
|---|---|---|---|
| 1 | max-jobs advice unbounded | folded and capped like every table; `data-levels=4`, 114 px per row | agree on the symptom, not the cause — the nesting, `UX-831` |
| 2 | readers section redundant | five labels, verbatim the picker's, 411 px below it | agree — `UX-822`, §5b |
| 3 | base runtime leads "worth optimizing first" | leader here is `storm.bst`, `is_foundation: false`; `bga-foundation` in no guide | challenge the remedy: declare, do not refocus — `UX-832` |
| 4 | deciles, p95, p99, mean | payload has 16 marks, the twin draws 5, mean unpublished | agree — `UX-827`, §2f |
| 5 | header too tall; logo, picker, footer | 128.5 px sticky (14.3%), line 2 a 149-char path; run-nav and handoff already in the rail; a footer exists | agree on the budget — `UX-828`, §3i |
| 6 | tables without filters | filters at the cap only (§3d): `elements` 25 of 1,202 with 3, `leaf_analysis` 40 of 135 with 1 of 5 sortable; the four named blocks are `dl.pairs` | decline as designed; the guard on capped tables — `UX-835` |
| 7 | a guideline for user-facing strings | the rule is in three sections and no guard; 5 bare ids, 37 visible keys, one pipe key | agree — §4g, `UX-824`, `UX-825`, `UX-826` |
| 8 | custom source plugins | `blast.py` heuristics over shipped kinds only | agree, as a declaration — `UX-833` |
| 9 | intervals From shows a monotonic value | "497003.7 h", `data-raw=1789213279678403` | agree — `UX-823` |
| 10 | serial chains ranked; fan-in list | one longest chain; `fan_in` carries counts, five joined fields draw no column | agree — `UX-830`, `UX-829` |
| 11 | "Which run is this?" to a subpage | a chapter, closed at landing, 600 px, nine screens down | decline: `UX-285` puts reference last; a subpage costs a click (§3b) for a chapter nobody scrolls to |
| 12 | width-at-level twin always open | the twin is behind "as table", `offsetParent === null` until clicked; no `aria-expanded` | decline the premise; the state is unannounced — `UX-834` |

On point 6 the owner's page may differ from these two: the census tool
reads an export and prints its structure, so `python3
tools/dev_page_census.py <export.html>` on their own file — once
`UX-836` makes it list tables — is the measurement this round could
not take.

## What the review found on its own

Eight findings, each measured on the walk capture and re-measured on
the synthetic export: a bare `UX-14` in a finding's caveat and four
more ids at scale; 47 `span.section-key` nodes visible; the From
column above; the readers table; five of seven joined fields with no
column on `elements`; `a.path-box`'s accessible name
"toolchain.bst0.0 simport"; `button.twin-toggle` without
`aria-expanded`; the header's path. The controls census: 28 classes,
0 differing from label. Type scale {13, 15, 17, 21} px, 72 chars per
line, contrast 17.4:1 body and 5.7:1 muted, first accent at 411 px on
the decision's link — §4f and §5 hold.

## Filed

`UX-822` to `UX-836`: fifteen rows, ten of them the owner's, five the
review's. Four styleguide sections carry the rules — §2f (a
distribution twin draws every mark), §3i (the header budget), §4g
(reader-facing strings, the list), §5b (what the header says is not
said again) — each with its §7 row naming the filing that will guard
it. The gate improvements: `UX-824` (one guard reading both exports
for the register), `UX-835` (a capped table filters what it sorts),
`UX-836` (the census lists tables — the numbers this round took by
hand).

## Brainstorm, not filed

- **A reader's first screen per role.** The decision card is one
  sentence for everyone; the picker promotes sections but the card
  does not change. A card per reader is `readers[].leads_with` drawn
  as the card — a rule for a round that measures it.
- **The rail's chapter counts as a budget.** 79 links, 9 visible;
  §3h gave disclosure; a count per chapter row ("· 12") is what a
  reader scans before opening.
- **Element card as the fan-in home.** `UX-829` puts the incoming
  names there; the card is where "why is this on the path" is asked,
  and the blast list is already its neighbour.
- **A footer that earns its line.** Version, contract, and the two
  links; nothing the header repeats.

## Standing

The suite's shape, derived by `dev_shape_budget.py` and printed by
`dev_close_task.py --check` (`UX-690`):

```text
shape         files   CI seconds    share
unit            453       754.2s    47.1%
sweep             1         2.1s     0.1%
journey           2         0.1s     0.0%
browser          53       805.7s    50.3%
enormous         20        39.9s     2.5%
```

## Process, measured

- The review agent measured 28 tables one CDP call at a time because
  `dev_page_census.py` lists none — `UX-836` is the fix; the session's
  own scale pass took one script and one browser boot.
- The walk capture has 3 elements: right for the planes, wrong for
  volume. Every volume claim was re-measured on `gen-synthetic`
  (Plane 1 only), so the max-jobs and interval claims have one
  fixture each. A Plane 2 fixture at 100+ elements is what `UX-831`
  and `UX-823` will need to close.
- The agent's first CDP port answered `/json/version` and hung on
  navigate — a stale listener from yesterday's walk; the process's own
  port worked. `tests/browser.py` could refuse a port it did not open.
- The shape derivation calls nine of fifteen filings judgement on the
  contract-surface rule (`bga/schemas.py` in the fix); the six that
  name a viewer or tool file and a guard are the tracks.

## Agents

One run — 1 `general-purpose` on `sonnet`, the review's driving half;
the judging, the scale re-measure and every filing were the session's.

| | |
|---|---|
| general-purpose | the design review on the walk capture; 205k tokens, 137 calls, 20.5 m; eight findings, ten claims measured |
| session | the 1,202-element re-measure (`r115/measure_scale.py`), the challenge, fifteen filings, four styleguide sections |
