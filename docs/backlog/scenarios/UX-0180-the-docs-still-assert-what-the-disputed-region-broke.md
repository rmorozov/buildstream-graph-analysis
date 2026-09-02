# UX-180: the docs still assert what the disputed region broke

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-170 (the fix the docs trail), UX-138 (the glossary), UX-135 (the README budget) | **Topic:** docs

## Motivation

UX-170's mechanism landed and holds (the −25% same-commit pair now
answers `WITHIN THE BASELINE SET'S OWN OBSERVED RANGE`); its
documentation trail did not keep up, and the round-19 review collected
the debris:

1. `real-project.md:784-786` still states the fixed defect in the
   present tense — "still calls the widest one `IMPROVED (-25.0%)`" —
   committed in the same push that makes that sentence false, and
   UX-170's own Required Fix ordered this claim to "become whatever is
   true after the fix".
2. The **fourth duration verdict is missing from every verdict list**:
   `cli.md:474` and README's verdict sentence both enumerate
   improved / regressed / no significant change / not comparable.
3. `bga/compare.py:818-821`'s docstring — the gate "fails exactly when
   a human reading the report would call it a regression, never a
   second, silently-different definition" — is now false twice over
   (band widening and the disputed region), and `cli.md:484` repeats
   it. UX-170's log says the divergence is documented there; it says
   the opposite.
4. The UX-176 fastest/slowest correction shipped unmarked (bare word
   swap, no annotation), against the convention its own batch applied
   one file over.
5. UX-174's `directory:` keying claim carries no provenance note —
   its acceptance required one, measured preferred.
6. **The glossary has no rows for the round's load-bearing terms**:
   blast, resource, keying (ref vs content), work (vs wall clock),
   building vs assembling. Five terms, three surfaces, zero
   definitions — the exact drift UX-138 was filed against.
7. README is at 266 lines against UX-135's ≤250: trim the four-line
   monorepo addition's neighbors or annotate the budget with the
   reason — silently exceeding a measured target is how 420 became
   "430".

## Required Fix

As numbered; the gate docstring (3) should state the two divergences
and point at UX-170's disputed-region rationale rather than promising
an equivalence that is deliberately gone.

## Out of Scope

- The band mechanics (verified holding).

## Acceptance Test

The docs-commands suite covers the corrected sentences; a grep test
pins the four-verdict list in both files; the glossary rows exist and
`make lint-docs` stays green; README ≤250 or the budget annotation
exists with the number restated.

## What was built

All seven items.

1. `real-project.md`'s defect sentence now states what is true after
   `UX-170`: the widest pair falls outside the band while still being a
   duration the baselines themselves reached, and answers **`within the
   baseline set's own observed range`** rather than a verdict.
2. The fourth verdict joined both verdict lists (`cli.md` and
   `README.md`). `design/architecture.md` carried the same stale claim
   *and* `UX-176`'s fastest/slowest error — it now names 2712.4s as the
   fastest run and says the band is unchanged, the verdict withheld.
3. `regression_exceeds_threshold`'s docstring gained **"Where the gate
   and the verdict now diverge"**, naming `UX-59`'s band and
   `UX-170`'s disputed region, stating that both divergences are
   deliberate and neither is silent, and that a pipeline wanting the
   band's judgement should read `verdict` rather than only the exit
   code. `cli.md:484` says the same.
4. The `UX-176` correction's remaining un-fixed site was
   `architecture.md` (see 2) — corrected there rather than annotated,
   because a design document is *current* under the style guide's rule
   2; the history of the correction already lives in `UX-176`'s file
   and `round-18.md`.
5. `UX-174`'s `directory:` claim carries measured provenance, on
   BuildStream 2.7.0: the git plugin's `get_unique_key()` returns
   `[original_url, ref]`, BuildStream adds the staging path beside it
   (`_elementsources.py`: `key_dict["directory"] = source._directory`),
   and three real `%{full-key}` values show that `directory:` is keyed
   *and* narrows nothing.
6. Five glossary rows in `docs/README.md` — resource, blast, keying
   (ref vs content), work vs wall clock, building vs assembling. Five
   terms became ten.
7. README trimmed **266 → 249** lines, inside `UX-135`'s 250-line
   budget, by compressing prose rather than dropping content (the
   takeaways paragraph, the baseline blockquote, the install and
   Plane 2/3 sections).

Tests: 5 new in `tests/unit/test_docs_links_and_commands.py`. The
verdict guard reads the four verdicts out of `compare.py`'s
significance chain rather than pinning literals, so renaming one
reddens instead of leaving two documents quoting a string `bga` no
longer prints. Each guard was falsified by reverting its fix.

**Caught by an existing guard while doing this:** the bst-gated tier
had grown to 43 tests against a pin of 42 in `.github/workflows/ci.yml`
(`UX-182` added one). Pin updated deliberately, which is what the guard
exists to force.
