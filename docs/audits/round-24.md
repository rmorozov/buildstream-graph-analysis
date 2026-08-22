# Audit round 24: the relationship layer already exists — it is not published

Run on 2026-08-22, same retained environment as rounds 10-23, against
`main` at `b44caa6` (round 23's whole slate, UX-207..UX-214, landed).
One input: a third external review of the shipped viewer, evaluated the
same way as the previous two — claim by claim, against the code, with
every premise checked before any of it is agreed to.

## The short version

The review's direction is right and its headline sentence is the best
one-line statement of where this tool is:

> the next improvements should not make the page prettier; they should
> turn existing BGA facts into stronger navigation and investigation
> primitives.

Its diagnosis — *the missing thing is relationships between existing
information* — is correct. Its **cost model is wrong in a way that
matters**, and in one direction that makes the work cheaper rather than
dearer.

## The finding: `ElementJoin` is computed and never published

The review proposes an element inspector showing, per element: critical
path share, build time, recoverable saving, blast radius, achieved
parallelism, and the Plane 2/3 evidence underneath. It calls this
"essentially a cross-reference popup over the report", and separately
proposes a three-plane "investigation ladder" as new work.

Both already exist, joined, in one dataclass. `bga/correlate.py:141`:

```text
ElementJoin
  element, declared
  Plane 1   on_critical_path, critical_path_share,
            potential_saving_us, saving_share, blast_radius
  Plane 2   cores_busy, cpu_coverage, requested_jobs,
            native_findings, unused_dependencies,
            dominant_binary, serial_binary, peak_rss_kb
```

`_plane2_view` (`correlate.py:277`) builds the Plane 2 half out of
`per_element_parallelism`, `cpu_time.per_element` and
`peak_memory.per_element` — all per element, all already computed.

Measured, on the state of `main` — and this is the second version of
this paragraph. The first said "text only", which is wrong:
`bga correlate --format json` exists and emits the join, eleven rows on
`examples/06`, every `ElementJoin` field present. Checking it is what
this round is for, including when the claim is mine.

What is actually true is narrower and sharper:

```text
bga correlate --format json   emits the join: 11 rows, all fields
its `schema` key               absent — the payload is unversioned
bga correlate --schema         "correlate produces no versioned JSON output"
schemas.names()                ['analyze/v1','blast/v1','compare/v1','store/v1']
bga view payloads()            does not serve it
analyze/v1 Plane 2             run-level only: plane2_coverage, utilisation
                               no per-element parallelism, CPU or memory
```

So the relationship layer is real, is computed on every correlate run,
and is **emitted as an unversioned blob that nothing can consume**. It
carries no `schema` stamp, so `UX-190`'s contract does not cover it; no
view-hints, so `bga view` could not render it generically even if it
were served; and it is not served. `bga view`, CI and every external
consumer are blind to it.

That is not "add a relationship layer to the viewer". That is
`UX-206`'s pattern for the fourth time — the analysis already knows and
the contract does not say — with a twist the earlier three did not
have: here the JSON is already correct and already shaped. What is
missing is the stamp, the schema and the wiring, which makes this the
cheapest of the four and the one the rest of the round waits on.

**Filed as [`UX-215`](../backlog/scenarios/UX-0215-publish-the-join-the-tool-already-computes.md),
High, and it is the enabler for most of the rest of this round.**

## The defect: last round shipped 19 links to nowhere

`UX-208` gave every row of an element-column table a generic Inspect
affordance, anchored at `#${cssId(uid)}`. Nothing in the page has ever
set that id.

Rendered `examples/06` and resolved every anchor:

```text
inspect links           19
distinct targets        11   (#element-core-bst, #element-lib-b-bst, …)
ids present in page     21   (all of them section keys: summary,
                              headline, floors, signals, …)
unresolvable targets    11   of 11
```

Every Inspect on the page is dead. `wireJumpBox` scrolls by
`[data-element="…"]` and works; the anchor `UX-208` shipped uses a
different scheme and matches nothing. My own round-23 work, and the
guards I wrote for it asserted that the affordance *exists* — never
that it *arrives*. The same failure class this project keeps finding,
this time in the round that was about finding it.

Filed as clause 1 of
[`UX-216`](../backlog/scenarios/UX-0216-every-element-is-one-object.md),
because the fix and the element identity it implies are the same work.

## Premises checked, and where the review is wrong

| review claim | verdict |
|---|---|
| "the schema already carries descriptions, so metric popovers are almost free" | **False where it matters.** `floors` has 0 described children and no description of its own; so do `capacity_verdict`, `occupancy`, `utilisation`. `certified_us` — a lower bound, not a prediction, and the most misreadable number the tool publishes — says nothing. The viewer already renders descriptions; the missing thing is the descriptions. `UX-220`. |
| "if the compare report already contains per-element deltas, [culprit] is mostly rendering" | **False.** `compare/v1` carries whole-run floor deltas and per-*category* attribution deltas. There are no per-element deltas anywhere in it. The idea is good; it is a payload item first. `UX-221`. |
| "BGA has three planes … the viewer could exploit that" (presented as new) | **Half true.** The per-element three-plane join exists (above). What is missing is publication, not analysis. `UX-215`. |
| "the missing capability is cross-navigation" | **Understated.** The cross-navigation was *shipped and is dead* (above). |
| findings should show evidence | **True, and cheaper than stated.** Every finding already carries a structured `evidence` dict — measured on `examples/06`: `cache-hit-ratio` → `hit_ratio, built_elements, cached_elements, run_mode`; `time-concentration` → `path_us, share_of_path, chain_bound, rows`. `renderFindings` reads `id, severity, title, detail, elements` and drops `evidence` on the floor. `UX-217`. |
| "what if I fix these" needs the projected values | **True, and they are published.** `signals.optimization_horizon` carries `saving_us`, `makespan_after_us` and `cumulative_saving_us` per step — plus `entering`, the elements that *join* the critical path once that one is fixed, which the review did not know about and which is the honest reason the savings stop adding. `UX-219`. |
| "resist adding more charts" | **Agreed, and already settled.** This is Direction 7's standing position, not a new recommendation. Recorded as agreement, not filed. |

## One design disagreement worth recording

The review asks for the element inspector as a **drawer** — a side
panel that opens over the report. Declined in that shape.

A drawer introduces overlay and layout machinery into a page that has
none, and it is the one part of the report that would not survive the
things this viewer is built to survive: an export opened from a
downloads folder, a print, `filter: grayscale`, a pasted anchor. The
same cross-reference value comes from a **section** — one more
`<section data-section="element-…">` prepended like `UX-207`'s decision
panel — which is linkable, printable, exportable, collapsible by the
machinery that already exists, and which makes `UX-208`'s dead anchor
resolve as a side effect rather than needing a second mechanism.

Same content, same click, none of the new machinery. `UX-216`.

## What the review did not look at: the loop, not the report

Every item the review proposes improves **one reading of one report**.
The friction this tool is actually built around is a *loop*:

```text
capture → analyze → read → change something → capture again
                              ↑                     │
                              └── did that help? ───┘
```

and the loop is where the repetition lives. Three things were filed
from walking it rather than reading the page:

- **The next three commands are always the same shape, and always
  retyped.** The page knows the run path, the project, the diagnosis
  and the top element. The exact `bga blast …`, `bga capture …`,
  `bga compare …` lines can be *rendered*, copyable, chosen by the
  published diagnosis — and the choice belongs in the payload, so the
  terminal and CI give the same next step as the page.
  [`UX-218`](../backlog/scenarios/UX-0218-the-next-step-is-a-command-you-can-run.md).
- **The investigation is not resumable.** `UX-211` put the *view* in
  the link. What is not anywhere is the *decision*: "I am working on
  `core.bst`, I already rejected `lib-b.bst`." A working set in the
  same fragment channel makes the loop resumable and shareable, with
  no server write — which the security posture forbids anyway.
  [`UX-225`](../backlog/scenarios/UX-0225-the-working-set-travels-in-the-link.md).
- **"Did my fix work?" is answered by hand.** The store holds every
  run; `bga compare` judges a pair; the trend draws the set. Nothing
  answers it *for the element you were working on*.
  [`UX-226`](../backlog/scenarios/UX-0226-what-happened-to-this-element-since-last-time.md).

## Standing

Round 23 made the first screen a decision. Round 24's argument is that
the decision is a dead end without the object it names being reachable
— and that the object is already assembled, one module away from the
document that would carry it.

Recommended order: **UX-215 first** (nothing else is honest without the
join being published), then **UX-216** (which fixes a live defect and
gives every later item its anchor), then **UX-217** and **UX-218** (the
two that change what the reader does next), then **UX-219..UX-226** as
the slate allows. **UX-221 and UX-226 both want per-element history and
should land together or in that order.**
