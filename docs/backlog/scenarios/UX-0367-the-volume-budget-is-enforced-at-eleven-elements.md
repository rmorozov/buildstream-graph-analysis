# UX-367: the volume budget is enforced at eleven elements

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-360 (the volume budget), UX-187 (a report you can read at four thousand elements) | **Serves:** anyone whose project is bigger than the fixtures | **Topic:** viewer

## Motivation

`UX-360` gave the page two budgets and a guard that holds them. The
guard parametrises over `pages.FIXTURES` — `golden` and `macro_micro` —
which are **11-element runs**. Measured against the 1,202-element
synthetic run, the same page:

```text
                    budget   golden   macro_micro   scale (1,202)
opened height       34,000    14,493       28,213          70,577
words               12,000     5,279        9,879          33,835
controls               800       409          659           1,834
```

**Every budget is exceeded by 2-3x at a realistic size, and no guard
runs there.** The bounds were set with a fifth of headroom against the
larger *fixture*, and the larger fixture is two orders of magnitude
smaller than the run `bga gen-synthetic` calls a scale probe.

This is `UX-360`'s own argument turned one level out: a bound nothing
can reach is not a bound, and a bound measured only where the page is
small is a bound that has never met the page.

Round 2 found four defects at 1,202 elements that were invisible at
eleven. The volume budget is the fifth.

## Required Fix

The budget guard runs at scale, and the bounds say which size they are
for.

- Add the synthetic run to the guard's population — it is generated from
  a seed, so it costs a `gen-synthetic` rather than a fixture in the
  tree, and `tests/tiers.py` already has a place for a file that heavy.
- State the budgets **per size class** rather than as one pair. A page
  that is 70,000 px at 1,202 elements may be acceptable; what is not
  acceptable is that nobody decided.

If the scale page cannot meet a bound anybody would set, that is the
finding and it belongs in the item that follows from it — `UX-366`'s cap
is one lever, chapter folding is another.

## Falsification

Export the seeded 1,202-element run, boot it, and assert the same three
numbers the round-56 guard asserts. It fails today at 2.1x, 2.8x and
2.3x. A guard that passes on `golden` and `macro_micro` and is never
asked about scale is the state this item is about.

## Out of Scope

Making the page smaller. That is `UX-366` and whatever follows it; this
item is about measuring at the size that matters, and about the guard
that measured the wrong two runs for a round and a half.
