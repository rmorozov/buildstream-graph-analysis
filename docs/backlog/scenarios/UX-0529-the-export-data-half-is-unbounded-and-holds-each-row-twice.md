# UX-529: the export's data half is unbounded, and holds each row twice

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-360 (the page-half budget), UX-526 | **Serves:** anyone attaching a report of a large project | **Topic:** viewer | **Area:** bga/viewer

## Motivation

```text
                      @1,202       @4,002
report JSON          628 KB      2,042 KB     427 B per element
page half            294 KB        294 KB     PAGE_BUDGET_B 300,000 — holds
export               1.0 MB       2.4 MB      EXPORT_BUDGET_B 8 MiB — reports only
```

`PAGE_BUDGET_B` bounds the hand-written half and `EXPORT_BUDGET_B`
only *reports*, so the data half meets the ceiling at about 13,000
elements with nothing between. And every row past the 40-row bound
is present twice — once in the JSON, once as a hidden `<tr>`
(`UX-526`) — which is the page's largest single duplication.

## Required Fix

The data half gets a budget of its own per size class, asserted the
way the page half is, and the per-element embedding is what pays for
it: the elements table embeds the rendered rows and a reference to
the rest, which the focus path fetches (served) or expands from a
compact form (export).

## Out of Scope

- `EXPORT_BUDGET_B` itself — it stays the outer ceiling.

## Acceptance Test

Data-half bytes at 4,002 pasted before/after; the composition guard
red if the data half exceeds its class budget.

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

The two seeded runs, exported before the change (`page` is the file
with every data block stripped; `schemas` is apparatus, `UX-342`):

```text
                elements     page   schemas       data       file
scale              1,202  302,757    84,516    629,385  1,016,963
xl                 4,002  302,757    84,516  2,042,989  2,430,567
```

~515 B per element, and `EXPORT_BUDGET_B` (8 MiB) the only thing above
it — reached at about 16,000 elements. `elements.blast_radius` and
`elements.criticality_probability` are 60% of it between them.

**The item's other half was already closed.** "Every row past the
40-row bound is present twice — once in the JSON, once as a hidden
`<tr>`" is `UX-526`, done earlier this round: `<tr>` in the DOM went
1,545 → 273 at 1,202 elements. Nothing here re-does it, and the file
never held rows twice — that duplication was in the booted page.

### The close, measured

```text
                 data before   data after     file before    file after
golden                29,700       29,700         417,771       417,771
macro_micro           79,820       79,820         467,891       467,891
scale                629,385       70,222       1,016,963       458,440
xl                 2,042,989      194,536       2,430,567       582,754
```

`DATA_BUDGETS` is (50, 100_000) and (4_100, 240_000) — the volume
budget's own class boundaries, at ~1.25× the largest run in each.

### Mutations

| mutation | red |
|---|---|
| `DATA_COMPACT_MIN_B = 20_000_000` (no compaction) | 4 — both class-budget clauses at scale/xl, both compact-form clauses |
| `DATA_COMPACT_MIN_B = 0` (compact always) | 2 — `..._is_still_readable_json[golden, macro_micro]` |
| `load()` stops calling `inflated` | 4 — the probe's `fetch` throws |
| `inflated()` loses its `try`/`catch` | 4 — same |
| the compacted document drops a key | 2 — `..._is_the_same_document[scale, xl]` |
| the large class's budget → 2,400,000 | 1 — `..._met_from_far_below[4100]` |

### A guard of mine that did not discriminate

`test_the_manifest_answer_counts_the_compact_block` asserted
`offered(run, "report") is True` against a compacted export. Deleting
the `bga-<name>-gz` branch from `offered` left it **green**: `_offered`
derives the manifest from the documents being embedded, so a compacted
payload is listed exactly as a plain one is and every other path in
that function already returns `true`. The branch was dead code and the
clause could not have caught anything. Both removed; the note in
`offered` says why, so it is not re-added.

### Deviation from the Required Fix

**Yes, in mechanism.** The Required Fix names one: "the elements table
embeds the rendered rows and a reference to the rest, which the focus
path fetches (served) or expands from a compact form (export)". That is
a payload change — `analyze/v6` one item after v5, a served endpoint
for the remainder, and the table's row source rewritten. What shipped
is the transport: the same document, gzip+base64 in one
`application/octet-stream` block, inflated by `load()` before it
reaches a network the export does not have. It meets the clause the
fix exists for — the data half has a budget per size class and is
inside it, 89-90% smaller — changes nothing about what the page can
show, and needs no contract move. The payload-shape half is not done
and is not filed: nothing measured here asks for it.

### Verification

```text
make test-touching        104 files · 1927 passed, 8 skipped in 344.19s
the new file alone         17 passed in 40.16s  (LARGE, tiered on landing)
make lint                  clean
```
