# Round 130 — navigation chooses; the Store section manages

Run on 2026-09-21. The checkout arrived shallow, with only `work` and no
configured remote. Main was fetched explicitly from the repository URL and
the branch rebased to `70765b09`; the two earlier local review commits were
already superseded by main's rounds 120–129 and were dropped. The measurements
below were then re-checked against that rebased tree.

```text
design review   all-plane export plus served 100-run store, Chrome 153, 1440×900
controls        run navigation, finding actions and store disclosure; 0 differ from label
filed           UX-917, UX-918
```

## Seen before measuring

- The sticky rail begins with report identity and run choice; it reads as the
  place that changes *which report* is open.
- The Store chapter is evidence about the population: trend, distribution,
  size and the window into older snapshots.
- Findings are cards. Their first 40 are visibly bounded, but a visual fold
  alone cannot establish that their controls stopped costing the document.
- Per-table tools remain local and population-independent; they are not a
  candidate for store-wide management.

## Measured

The served synthetic report is 7,186px high and has 402 controls: 364 buttons,
30 inputs and 8 selects. Its 15 findings contribute 43 controls. The run picker
is a 223×73.7px block at `(64.5, 114.5)` in the 240px sticky rail; it contains
one 223×19px select and one 112.3×22.7px Previous-run button. Two stored runs
produce two options.

Snapshot growth itself is already bounded correctly. On a served 100-run
store, the picker held 12 options, the Store table 12 rows and its plot 27 SVG
marks, with exactly one typed-id field and one **Show all 100 snapshots** door.
`UX-528` is holding its intended axis. No snapshot-count-dependent global
control defect remains on the landed page.

Finding growth has a different hidden cost. Rendering otherwise identical
findings with one copy action each produced:

```text
findings             1    15    40    120
visible cards         1    15    40     40
controls              1    15    40    121
controls in hidden    0     0     0     80
```

`boundCards` hides whole cards so their anchors survive. The visible-card
guard passes while interactive descendants continue linearly. The current
catalog has 30 ids, but that is today's producer count, not a viewer bound.

## Judged

The run picker is in the best place for **navigation**: it changes report
context, remains visible, and preserves the section hash. It is the wrong
place for **management**. Pruning is occasional, destructive and meaningful
only alongside store count, bytes, history and protected runs. Mixing it into
the rail would violate §4c's scope rule and Apple-style deference: an
administrative action would compete with the page's primary reading path.

Per-run Delete buttons are rejected: they grow with the store, make a frequent
navigation list hazardous, and turn a policy operation into repeated manual
decisions. Browser-side pruning is also rejected: the report is read-only, and
the CLI already supplies its explicit confirmation boundary. A fixed global
toolbar loses the evidence that makes the choice intelligible. A separate
management page is unnecessary for three policies and would split context.

## Proposed

Styleguide §3j gives hidden interactive DOM the same population bound as
visible cards. Keep lightweight anchor shells, hydrate one on fragment entry,
and hydrate all only after **Show all**.

Styleguide §3k separates snapshot navigation from management. Collapse the run
selector, Previous and Latest under a one-row Run summary in the rail, with a
single **Snapshots…** link to the Store section. Put whole-store facts,
protected-run explanation and copyable list/dry-run commands there. Pruning
remains CLI-only; export omits served-store controls.

## Controls

| class | observed | verdict |
|---|---|---|
| `.run-picker select` | chooses the report and preserves its hash | correct rail navigation |
| `[data-run-jump]` | Previous/Latest only when live | correct rail navigation |
| finding copy/investigate | hidden with cards but still materialised | fails §3j at 120 |
| `[data-role=store-show-all]` | one door beyond the 12-run window | correctly fixed-cost |

## Findings

1. `UX-917` — hidden findings keep live controls. Nearest closed rows:
   `UX-413` and `UX-526`.
2. `UX-918` — snapshot navigation and management need separate loci. Nearest
   closed rows: `UX-394`, `UX-528` and `UX-300`.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| design-reviewer | GPT-5.6 Sol | control growth and snapshot-management locus | unmetered | unmetered | 24 m | split all-plane and served fixtures; the checkout needed an explicit main fetch |
