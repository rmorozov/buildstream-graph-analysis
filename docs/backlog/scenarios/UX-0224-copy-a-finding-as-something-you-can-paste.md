# UX-224: copy a finding as something you can paste

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-217 (the evidence it carries), UX-115 (the CI comment renderer) | **Topic:** viewer

## Motivation

The report ends its life in a pull request, a chat message or a ticket,
and getting it there is manual: select the finding, lose the evidence,
retype the numbers, re-find the element name.

`UX-115` already renders a CI comment from a payload, and `UX-208`
already ships a clipboard helper with a `✓ copied` acknowledgment. A
Copy on each finding is those two things meeting.

```text
BGA finding: build is chain-bound
  critical path 3610s, 94% of wall-clock
  scheduling wait <1%
Top opportunity: core.bst — 12.05s recoverable, 18.6% of path
Suggested action: reduce the work on the chain, not the builder count.
Run: 20260821T170127Z
```

The last line matters as much as the first: a pasted finding without
the run identity is an assertion nobody can check, and `UX-178`
established that the identity must round-trip.

## Required Fix

1. A Copy button per finding, emitting plain text: title, evidence in
   its declared units, the elements named, the published next step from
   `UX-218`, and the run identity.
2. The same text, from the same function, as `--format ci-comment`
   already uses where the shapes overlap — one renderer, so the pasted
   finding and the CI comment cannot word the same conclusion
   differently.
3. Markdown when the platform will take it, plain text otherwise; the
   copy affordance says which.

## Out of Scope

- Posting anywhere. No network from the page.
- A new finding format, or changing `--format ci-comment`'s output.
- Copying the whole report (the export is that).

## Acceptance Test

The copied text for `time-concentration` on `examples/06` contains its
published `path_us` in the same unit the page shows, the element it
names, and the run stamp — asserted against the payload, not against a
golden string. The renderer is shared: asserted by reading the source,
not by the two happening to agree today (`UX-214`'s lesson).

Mutations, each asserted red: drop the run identity → the round-trip
guard fails; give the copy its own wording of the conclusion → the
one-renderer guard fails.

## Outcome (round 26)

Clause 2 asks for one renderer shared with `--format ci-comment`. The CI
comment is Python and the viewer is JavaScript, so across that boundary
"one renderer" is only honest one way: **the text is rendered in the
pipeline and published as `findings[].copy_text`**, and the page copies
a string rather than wording one. The same reason UX-218's commands are
decided in the pipeline and UX-207's diagnosis is.

That makes the one-renderer property checkable by reading the source, as
the acceptance asks: `app.js` may contain `finding.copy_text` and must
not contain the string `BGA finding:` — and neither may any other viewer
module. A page that worded its own conclusion would fail on the words,
not on the two happening to disagree today.

`copyButton` and its `✓ copied` acknowledgment already existed from
UX-208, so the affordance is that function meeting a published string.

### Two things the golden fixture showed immediately

The first draft produced text that was worse than useless:

```text
  blast radius {'base.bst': {'downstream_count': 2, 'weighted_duration_us': …
  category untracked_tail_us
  category 0.0s
```

A nested `blast_radius` dict rendered as 400 characters of Python
`repr` into the middle of a paste, and `category` and `category_us` —
two different values — were both reduced to the label `category`. Two
numbers under one name is worse than an ugly one.

Non-scalar evidence is left out now, and the label is the published key
verbatim, so a paste names the field a reader can look up. Both are
guarded, and both guards assert against the payload's own numbers rather
than literal strings.

The units come from `EVIDENCE_QUANTITIES` — UX-217's declaration of what
each evidence key *is* — not from a second table here. Blanking that
lookup reddens three guards.

**Mutations verified red and reverted:** drop the run identity (1 guard
— this task's first); give the copy its own wording in the page (1 — its
second); make the evidence lose its declared unit (3).

**Deviation from the Required Fix:** clause 3 asks for markdown "when
the platform will take it", with the affordance saying which. Not built:
the page cannot detect what a paste target accepts, and a button that
claimed to know would be guessing. Plain text only, which every target
accepts. Recorded rather than silently dropped.
