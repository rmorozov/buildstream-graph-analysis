# UX-774: the guide is at its band ceiling, and every round pays a trim

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** the round that adds a tool and finds an unrelated paragraph is what it has to delete | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

`test_a_paragraph_does_not_move_the_stated_figure` (`UX-607`) requires
1,024 B between the guide's size and the top of the 10 KB band it
states its size in. The band's ceiling is 56,320 B, so the guide must
stay under 55,296 B.

It does not want to. §6's module map gains a row per new tool, §7a
gained seven obligations, and the guide grew 7,279 B since
2026-09-06:

```console
$ git log --format=%h -40 -- docs/contributing/fixing-guide.md | tail -1
b96834e
$ git cat-file -s $(git rev-parse b96834e:docs/contributing/fixing-guide.md)
47974
$ wc -c docs/contributing/fixing-guide.md
55253 docs/contributing/fixing-guide.md
```

Growth is monotone and the band is fixed, so the guard's outcome is
already scheduled. Two of the last three rounds paid it:

| commit | B | Δ | what it was |
|---|---|---|---|
| `8997068` | 55,280 | −349 | round 106, trimmed to get under the limit |
| `17bf0b8`→now | 55,253 | −96 | round 107, `UX-744`'s module row over the limit |

Both trims fell on prose chosen for being cheap to cut, not for being
least useful — the second deleted a rhetorical clause and shortened a
list of placeholder shapes. The guard is honest about what it
measures (a two-file figure change is real, and round 84 paid it
twice) and it converts *the guide grew* into *delete something else*,
which is the wrong actuator. 1,067 B of headroom remain: one module
map row and one paragraph.

Nothing here says the figure should be unguarded. It says the guard
has one lever and the document has two problems, and the lever now
fires on the wrong one.

## Required Fix

A decision first, then a guard — this is judgement-shaped and the
options are not equivalent.

1. **The map moves out.** §6's module map is 103 rows and is the
   growing part; it is also the part a reader greps rather than reads.
   Give it its own file with its own derived figure, and the guide's
   prose stops paying for the tree's growth. `UX-689` already proposes
   the architecture document move into area pages — the same argument,
   one document over.
2. **The figure stops being stated in prose.** The guard exists
   because the size is written in two documents by hand. A derived
   figure — the shape `dev_touching.py --spread --write` has for the
   cost row — costs one tool and removes the two-file coupling
   entirely, and then the size may be whatever it is.
3. **Widen the band.** Cheapest, and it defers rather than fixes:
   at a 25 KB step the band is 25,600 B and this recurs in a year.

(2) is the one that matches how this repository fixes figures
everywhere else, and (1) is worth doing regardless. Whichever lands,
the Outcome states which and why, and the trims made under the old
regime are not reverted — they are recorded here as what the guard
cost.

## Out of Scope

- `UX-607`'s guard itself, unless the chosen option retires it.
- Rewriting the guide for length. A shorter guide is a different task
  and this one must not become an excuse for it.
- `docs/contributing/rules.md`'s copy of the figure — it is the
  second half of the coupling and moves with whatever the choice
  above does to the first; editing it alone is the two-file change
  `UX-607` exists to prevent.

## Acceptance Test

Add 2 KB of prose to the guide and run `make test`: green, and no
second document changed. Then mutate whatever derives the figure and
watch it red.

## Outcome

_Not started._
