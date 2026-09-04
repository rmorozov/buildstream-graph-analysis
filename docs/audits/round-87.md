# Round 87 — the `bga view` audit (2026-09-04)

The brief came from the repository's owner reading a report and not
trusting a control: pressing **Expand** twice left the page in a state
they could not explain. The round walked `bga snapshot` → `analyze` →
`view` → Perfetto on a three-plane capture of `examples/06`, and the
control turned out to be the smallest of what it led to.

## What landed

| | | |
|---|---|---|
| `UX-638` | table focus destroys the reading position | High |
| `UX-639` | the rail is dead while a table is focused | High |
| `UX-640` | the rail names the key, the heading asks the question | Medium |
| `UX-641` | the levels key is the identity function | Medium |
| `UX-642` | a structured fold forgets it was open | Low |
| `UX-644` | main is red — a map entry under the cap widened a module | High |

Four tracks in parallel worktrees, split on strict file ownership so
no two touched the same module: A owned `tablefocus.js`/`style.css`,
B `nav.js`, C `analyzer.py`/`schemas.py`/`structured.js`, D
`viewstate.js`. Two constraints made that split possible and are worth
keeping: `UX-639` was fixed without touching `nav.js` (focus is entered
in one place, so the rail's state is set there), and `UX-642` took the
`viewstate.js` route rather than adding an attribute in
`structured.js`, which kept that file with one owner.

## What the round measured that its own filings had wrong

Three of the six task files were written from a reading and corrected
by a measurement. This is the round's most useful output.

**`UX-638`'s mechanism.** The filed defect does not reproduce with a
plain enter/leave: Chrome restores the offset a shrinking document
clamped, by itself, when nothing scrolled in between.

```text
                       enter, leave        enter, read, leave
document height    40,578 -> 1,681 px      40,578 -> 1,681 px
scroll offset       5,954 -> 5,954         5,954 -> 14,497
the table's top       300 ->   300 px        300 -> -8,242 px
```

Track A's first probe sat in the left column and would have been a
false green on the unfixed page. One scroll inside focus — which is
what focus is for — spends the restoration, and the displacement is
8,543 px.

**`UX-640`'s "not a defect".** The filing recorded that a rail click
does not lose view state, reasoning that `captureView()` re-derives it
from the DOM. It does, when it runs. `wireViewState` delegates from
`#report` and `app.js:915` inserts the rail as a **sibling**, so for a
rail click it never runs. Filed as `UX-647`.

**`UX-642`'s population.** The filing said the larger fold population
was the broken one. Measured, `data-fold-path` is the *smaller* half
(12 vs 16 on `macro_micro`); the defect is that the two sets are
disjoint — `both = 0` on both fixtures.

## The merge hazards, all three of which fired

`UX-501`'s shape, three times, and every one merged **without a
conflict** into a wrong value:

```text
UNRESOLVABLE      base 58; B wrote 59, D wrote 59; the truth is 60
the loop figure   this branch 468, track C 465; the truth is 469
tiers.py          four rows, four places; resolution is "keep both"
```

A number two tracks each derive against their own tree is not a side
to pick — it is a sum to re-derive after the last merge. The tracks
predicted the first two in their reports and declined to write them,
which is why they were caught.

## The suite

```text
make test    28 failed, 6939 passed, 82 skipped, 17 errors
make lint    All checks passed!
```

Every failure is the real-`bst` family. Attributed by staging a
worktree at `b7cdd5f` the same way and running the same files: the
same tests fail identically on the base, with
`FAILURE Staging local files into CAS` — this sandbox cannot run real
builds. The first attempt at that comparison was wrong and worth
recording: an unstaged base worktree **skips** those tests
(`examples/01 is not staged`), which reads as 27 new failures rather
than as an invalid comparison.

One failure is not in that family:
`test_the_sections_are_still_as_tall_as_their_content`, which fired
under parallel load here and once in CI at 6.1x against a bound of 8,
while reading a steady 22.2x single-process. Filed as `UX-649`.

## Filed, not built

`UX-643` (the reader role as demotion), `UX-645` (the census floor
inside the width bound), `UX-646` (the fragment is one event behind
the fold), `UX-647`, `UX-648` (the palette's labels), `UX-649`.

`UX-643` is the round's one design decision and needs the
`bga:readers` mapping authored across ~51 sections before it is code.
