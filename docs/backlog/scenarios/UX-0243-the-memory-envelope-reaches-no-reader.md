# UX-243: the memory envelope reaches no reader

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** R5 — whose whole question is how many builds a machine can hold | **Topic:** docs

## Motivation

The second of `UX-237`'s three round-28 instances.

`compute_memory_envelope` (`bga/correlate.py`, called from
`bga/cli.py:141,172`) turns Plane 2's peak-RSS records into the figure
that decides whether `--builders` can go up — the one number in `bga`
that answers R5's question directly. Measured:

```text
git grep -l memory_envelope docs/
  docs/backlog/scenarios/UX-0104-…md   docs/backlog/scenarios/UX-0220-…md
  docs/backlog/scenarios/UX-0229-…md   docs/backlog/scenarios/closed.md
```

Backlog only. `README.md` says peak memory "is what decides whether
`--builders` can go up" and names no field, so a reader who believes
that sentence has nowhere to go next.

## Required Fix

1. Name the field and its unit where the guides discuss raising
   `--builders`, with the condition it needs (a Plane 2 capture — it is
   silently absent from a Plane 1-only run, which is the failure mode
   worth stating).
2. Say what it is an envelope *of*: concurrent peak, not the sum of
   peaks, and why summing would be the wrong bound.

## Out of Scope

- A fleet model. That is Direction 9 and R5's real gap; this is one
  field's documentation, filed because it is cheap and currently zero.
- `capacity_recommendation` — `UX-242`, filed separately for the reason
  given there.

## Acceptance Test

`git grep -l memory_envelope docs/` names an instructional document,
and the README sentence about peak memory points at it.

## Outcome — 🟢 Fixed & Verified

The field now has a subsection of its own in `docs/guides/cli.md`'s
**"How many builders, and what stops you"**, and the README sentence
that sent readers nowhere points at it.

**Clause 1 — named, with its unit and its condition.** It is a published
key of `correlate/v1`, which the guide shows rather than describes:

```text
$ bga correlate @last -f json | jq .memory_envelope
{
  "host_memory_mb": 16075, "builders": 4, "elements_measured": 9,
  "largest_element_peak_mb": 153.5,
  "at_observed_builders": {"builders": 4, "envelope_mb": 613.7,
                           "share_of_host": 0.038, "fits": true},
  "first_builders_that_does_not_fit": null
}
```

Every figure is in **megabytes**; `share_of_host` is a fraction. It
needs a Plane 2 capture and is silently `{}` without one — the failure
mode this item asked to have stated, and the guide states it as one of
three: no `--plane2`, no per-element peak RSS in the Plane 2 report, or
no host RAM recorded at capture time.

**Clause 2 — what it is an envelope *of*.** The envelope at N builders is
the sum of the **N largest measured per-element peaks**, as if those N
elements built at once and peaked at the same instant. The guide gives
both reasons the alternatives are wrong: summing every element's peak
counts memory that was never held at the same moment, and summing only
the *observed* concurrency answers a question about the run you already
have rather than the one you are considering. Both are upper bounds, and
for "is it safe to raise `--builders`?" an upper bound is the useful
direction to be wrong in.

Two clauses were added beyond what this item asked for, because they are
the two ways a reader would misuse the number:

- **No safety margin is invented.** `fits` is a strict comparison against
  the host's RAM with nothing reserved for the OS or page cache, so
  headroom below 100% is not the same as safe.
- **It projects only as far as it measured.** `elements_measured` bounds
  the table, which is why the constraint line reads *"measured over 9
  element peak(s), so it says nothing above 9"* rather than reporting a
  ceiling it never reached.

**The README now points somewhere.** It said peak memory *"is what
decides whether `--builders` can go up"* and named no field; it now names
`memory_envelope`, its contract, its unit, and links to the chapter.

**The guard** — `tests/unit/test_the_builders_question_has_a_document.py`,
12 tests, shared with `UX-242`. Falsified, ten mutations:

```text
M1   remove the whole chapter          -> 8 of 12 (the floor under the rest)
M2   the capacity subsection stops     -> instructional_document_names_the_field
     naming `capacity_recommendation`     [capacity_recommendation]
M3   the memory subsection drops its   -> subsection_states_the_condition[memory envelope]
     decline conditions
M4   drops "never held at the same     -> envelope_says_what_it_is_an_envelope_of
     moment"
M5   `graph binds at 2` -> `at 3`      -> binding_constraint_is_what_the_tool_computes
M6   `1.60 of 4 core(s) busy` -> 1.66  -> every_constraint_line_is_one_the_tool_prints
M7   `host_memory_mb: 16075` -> 16000  -> envelope_figures_are_the_tools_own
M8   README stops naming the field     -> readme_sentence_about_peak_memory_points_somewhere
M9   drops "largest measured           -> envelope_says_what_it_is_an_envelope_of
     per-element peaks"
M10  drops the unit                    -> envelope_names_its_unit
```

M4 did not land on the first attempt — the phrase wraps across two lines
and the `sed` pattern could not match it, which is `UX-244`'s hazard for
the second time in one round. It was rewritten as a Python replacement
on the wrapped literal and asserted before the result was read, rather
than counted as a green.

M5-M7 are the ones worth having. The guard recomputes both fields from
the committed snapshot (`examples/06-…/run` plus its `plane2.json`) and
requires every pasted constraint reason and every quoted envelope figure
to be one the tool prints **today**. A pasted number is a claim about the
tool, and the run is in the tree, so the claim is checkable rather than
historical (`UX-132`).
