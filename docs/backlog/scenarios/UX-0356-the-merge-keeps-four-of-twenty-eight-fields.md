# UX-356: the element join is "merged into the element table", and the merge keeps four of its twenty-eight fields

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-215 (publish the join), UX-338 (never draw one population twice), UX-289 (one element table) | **Serves:** anyone who opens the report to find out what to change | **Topic:** viewer

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

## Outcome (round 56, 2026-08-28) — 🟢 Done

### The gap, measured — against the rendered DOM, not the file

```text
macro_micro, element_join, 28 fields
  MISS  recommendations[].id                     0 on page /  23 not
  MISS  recommendations[].text                   0 on page /  23 not
  MISS  dominant_binary.binary / cpu_share / cpu_us / wall_us
  MISS  serial_binary.cpu_us / wall_us
  MISS  worst_redundancy.signature / example_cmd
        / total_duration_us / max_element_duration_us
  MISS  cpu_coverage, saving_share, native_findings[]
```

### After

```text
  ok    recommendations[].text                  23 on page /   0 not
  ok    dominant_binary.*, serial_binary.*, worst_redundancy.*
  ok    cpu_coverage, saving_share, native_findings[], unused_dependencies[]
  MISS  recommendations[].id                     0 on page /  23 not
```

Twenty-seven of twenty-eight. The one that stays is the slug, and
`DRAWN_ELSEWHERE`'s sentence now names it and says why — which is §1b's
first clause in one line: *a projection declares its losses.*

### The advice reads at the grade it deserves

```text
high  holds 44% of the critical path and fixing it is worth 12.1s
      (26.1% of the build), but runs at only 0.90 cores busy - it is
      waiting, not computing, and its native build asked for -j1:
      remove `notparallel` / raise its job count before touching its
      sources
```

In the element section, above the evidence and above the findings that
name the element, because it is the finished advice rather than
support for it. `data-severity` is the channel and the word is printed
in the badge beside the sentence — the same shape `renderFindings`
uses, declared in the palette guard's channel table so the tone is
never alone (§4.3).

The Plane 2 evidence behind those sentences — `dominant_binary`,
`serial_binary`, `worst_redundancy` — renders in a fold that announces
its depth (§3a.1): *"What Plane 2 saw · 1 level, 12 rows"*. Ninety-four
rows across nine folds on `macro_micro`.

`JOIN_EVIDENCE` is declared beside `SOURCES` and reads the same way, so
a field added to `correlate/v3` is a line here and no new code — the
property `UX-193` bought for sections, applied to the join's nested
half.

### `UX-349`'s rule, one level down

`worst_redundancy.example_cmd` equals `signature` on four of five
elements and differs on the fifth, where the normalisation replaced
`cmTC_0df0f` with `cmTC_<id>`. So a row is dropped when its value
already appears in the same block: the concrete command shows exactly
where it says something the signature does not, and the four
duplicates are one string twice rather than two rows.

### The instrument reads the DOM, and says so

The whole finding turned on `main.textContent` against
`document.body.textContent`: the export inlines the payload into
`script#bga-report`, so a `grep` over `report.html` finds every value
the payload has and concludes it reached the reader.
`test_the_sentence_is_not_only_in_the_embedded_payload` asserts that
distinction directly, so this file cannot quietly become a test of the
file rather than of the page.

### Bounds restated, each with its measurement

```text
page          244,088 -> 249,694 B   budget 248,000 -> 254,000
golden        329,444 -> 335,050 B   bound  335,000 -> 341,000
macro_micro   369,740 -> 375,346 B   bound  375,000 -> 381,000
data/page          2.860x -> 2.748x  bound      2.8 -> 2.6
```

**The data did not move at all.** Nothing was added to the payload;
sentences it already carried stopped being withheld. 5,606 B of page
to stop dropping thirteen of twenty-eight published fields is the
trade, and the bounds are restated rather than the sentences left in
`script#bga-report` to fit a number nobody argued.

The ratio note records something the number alone would hide: **two
rounds running have moved it in one direction**, against a synthetic
run whose data is fixed by construction, so it now measures the page
alone. A third restatement would make it a record of the page's growth
rather than a bound on it. That is `UX-360`'s volume budget, and the
note says so where the next person will read it.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `e9c091e`.

| # | mutation | reddened |
|---|---|---|
| R1 | the recommendations are dropped again — the defect itself | 4, including the field-coverage clause and the embedded-payload clause |
| R2 | the badge is kept and the sentence dropped — the *inversion* the item is named for | the same 4 |
| R3 | the nested Plane 2 evidence is dropped | 2: field coverage, and the fold-depth clause |
| R4 | the redirect sentence says it drops "nothing at all" | 2: field coverage, and `test_the_sentence_names_what_it_drops` |
| R5 | the evidence fold reports one row whatever it holds | 1: the fold-depth clause |

R2 is the one the rule is about. R1 and R2 redden identically, which
is correct and is the point: a page that shows a severity chip over a
withheld sentence has not half-succeeded, it has inverted the ordering
`§1b` states.

R3 left `test_the_evidence_is_the_plane_two_half` green, and that is
honest rather than a gap: `cc1plus` is *also* named inside the
recommendation sentence (*"85% of its measured CPU is one binary,
`cc1plus`"*), so the value really is on the page. The clause asserts
reachability, and R3's own second failure is what catches the fold.

### Deviation from the Required Fix

- The Required Fix said the remaining fields "belong with them — in
  the element section, behind the section's own fold, not as twelve
  more columns". Done as written, with one addition it did not ask
  for: `cpu_coverage` and `saving_share` are *scalars* and went into
  `SOURCES` as two more rows of the element pairs rather than into the
  fold. `cpu_coverage` is the caveat on `cores_busy` directly beside
  it — a low coverage makes that number a sample rather than a
  measurement — and §4a's rule is that a caveat lives where the number
  is, not behind a door.
- `recommendations[].id` is not rendered, and the Required Fix implied
  every field would be. It is a slug used as a key, the same class as
  `next_steps[].id`, which this item's own Out of Scope section
  excluded for that reason. Naming it in the redirect sentence is the
  rule the item actually asked for.
