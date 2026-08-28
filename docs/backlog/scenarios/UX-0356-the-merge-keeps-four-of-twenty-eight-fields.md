# UX-356: the element join is "merged into the element table", and the merge keeps four of its twenty-eight fields

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-215 (publish the join), UX-338 (never draw one population twice), UX-289 (one element table) | **Serves:** anyone who opens the report to find out what to change | **Topic:** viewer

## Motivation

Round 55 asked the user's question — *does everything the JSON holds
actually reach `bga view`?* — leaf by leaf, against the **rendered
DOM** rather than the exported file.

```text
                 payload leaves   reach a rendered node
golden                      327            292   (89%)
macro_micro               1,012            773   (76%)
```

The 239 misses on `macro_micro` are not spread thin. 142 of them are
one key:

```text
element_join     142      provenance    71      findings   11
wall_clock_share_us  7    elements       5      next_steps  3
```

`element_join` is `correlate/v2`, the Plane 1 x Plane 2 join, and role
R2's whole answer. It is in `app.js`'s `DRAWN_ELSEWHERE`, which is
`UX-338`'s honest mechanism — a population the page deliberately does
not draw on its own, with a sentence saying where it went:

> merged into the one element table (`elements`), which is `UX-289`'s
> rule applied to the columns `UX-215` added

The merge is `element.js`'s `SOURCES`, and it names four columns:
`cores_busy`, `requested_jobs`, `peak_rss_bytes`, `blast_radius`. The
join publishes twenty-eight fields. **Thirteen reach no rendered node
at all**:

```text
MISS  recommendations[].id                     23 values
MISS  recommendations[].text                   23 values
MISS  dominant_binary.binary / cpu_share / cpu_us / wall_us
MISS  serial_binary.cpu_us / wall_us
MISS  worst_redundancy.signature / example_cmd
      / total_duration_us / max_element_duration_us
MISS  cpu_coverage, saving_share, native_findings[]
```

The worst of them is `recommendations[].text`. The analyzer writes, per
element, the sentence a user came to the report for:

```text
holds 44% of the critical path and fixing it is worth 12.1s (26.1% of
the build), but runs at only 0.90 cores busy - it is waiting, not
computing, and its native build asked for -j1: remove `notparallel` /
raise its job count before touching its sources
```

Twenty-three of those on `macro_micro`. `severity` is rendered for
every one of them; `text` for none. Located in the DOM, the sentence
appears exactly once:

```text
inMain: false          (document.querySelector("main").textContent)
inBody: true
hits:   [{ tag: "SCRIPT", section: null, height: 0 }]
scripts:[{ type: "application/json", id: "bga-report", bytes: 57,939 }]
```

It is in the embedded payload the export ships so the page can boot
from `file://`, and nowhere else. A `grep` over `report.html` finds it
and concludes it reached the reader. It did not.

**Why this is High.** The page's whole argument is that it turns a
payload into a decision. Here the payload already contains the
decision, written in sentences, naming the flag to change — and the
page shows a severity chip beside it and drops the sentence. It is
also the second time a `DRAWN_ELSEWHERE`-style promise has been
believed rather than measured: `UX-338` established the mechanism and
nothing has ever checked that what it promises arrives.

## Required Fix

Styleguide §1b, in three clauses:

1. **"Drawn elsewhere" is a promise about fields.** Either every field
   of a redirected population arrives at the named destination, or the
   sentence names the ones that do not and why. A merge that keeps
   four of twenty-eight is a *projection*, and a projection declares
   its own losses.
2. **Where the payload publishes prose written for this reader, the
   page prints the prose.** `recommendations[].text` is not a
   supporting detail; it is the finished advice. It belongs in the
   element section, with its severity, at the same grade as
   `headline.top_actions`.
3. **The embedded payload is not a reader.** Any coverage instrument
   for this rule reads the DOM.

The remaining fields (`dominant_binary`, `serial_binary`,
`worst_redundancy`, `cpu_coverage`, `saving_share`) are the Plane 2
evidence behind those sentences and belong with them — in the element
section, behind the section's own fold, not as twelve more columns on
a table `UX-349` just finished narrowing.

## Out of Scope

- `findings[].copy_text` (4 and 11 misses). That is a *copy payload*,
  by design not rendered — the string a copy control writes to the
  clipboard. It is a true negative of the instrument, and the guard
  this item lands must exempt it by name and say why.
- `next_steps[].id` (3 misses). A slug, used as a key; the step's
  title and command both render.
- `wall_clock_share_us` (4 and 7 misses) and `elements.blast_radius`
  (5). These are formatted-value false positives: the raw microsecond
  values do not appear as strings because the page renders `4.0 ms`
  and carries the raw in `data-raw` under a key the instrument did not
  match. Worth fixing in the instrument, not in the page.
- `provenance`'s 71 — filed separately as `UX-357`, because the fix
  there is about a different promise.
- Re-litigating `UX-338`. Drawing the join as its own section again is
  exactly what that item forbade, and this item does not ask for it.

## Acceptance Test

Booted, both fixtures, every chapter open: every field a
`DRAWN_ELSEWHERE` population publishes either reaches a rendered node,
or is named in that population's redirect sentence. Asserted against
the payload's own field set, so a field added to `correlate/v3`
tomorrow joins the check without an edit. And, specifically: the
sentence above is readable on `macro_micro`'s page without opening the
JSON toggle.
