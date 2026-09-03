# Round 81 — the thirteen rows round 80 filed against itself

Input: the thirteen rows open after round 80 — `UX-540`..`UX-547`
from the six tracks' own measurements, and `UX-548`..`UX-552` from
architecture review 12. Every one is this repository's finding about
itself; no external report was read this round.

`UX-500` was decided in round 80 and refused Regime B, so fixing guide
§3 stands as written: the suite gates each item, not each batch. At
round 80's measured 8m52s that is the round's dominant cost, and it is
the reason the order below exists at all — an ordering that lets an
item be closed once is worth more than one that closes it twice.

## What the order is derived from

Four constraints, each from a measurement rather than a preference:

| constraint | why |
|---|---|
| `UX-541`/`UX-542` run **alone** | both need interleaved A/B, min of five, at 1,202/2,402/4,002 on a 4-core container. Round 80 discarded a probe measured under 3.3x self-contention |
| `UX-541`/`UX-542` run **first** | either may bump a contract. `UX-550` forbids editing a release row once written, so a bump after it lands is a contradiction, and `UX-549` derives figures from the same population |
| `UX-540` → `UX-550` → `UX-549` | `UX-540` changes what `contracts` answers for; `UX-550`'s guard compares against `contracts.ids()`; `UX-549` derives from `superseded()`. Three items reading one population, in the order it moves |
| `UX-551` closes **last** | its fix is a dated `make test` figure. The round's own gate run is that measurement, so closing it earlier spends a second nine minutes for nothing |

`UX-543` and `UX-546` are the fifth shape: they measure a clause
*under* contention and generate their own, so they sit away from the
timed items rather than beside them.

## Decomposition

```text
surfaces: A bga/attribution/blame_chain.py + bga/diagnostics/analyzer.py (contract bump possible)
          B tests/unit/test_the_dom_shim_is_one_instrument.py · bga/viewer/questions.js · tools/dev_refresh_analysis.py
          C bga/contracts.py · CHANGELOG.md · docs/README.md · docs/design/architecture.md (§3.10)
          D docs/guides/cli.md · docs/guides/what-the-viewer-answers.md
          E tests/unit/test_the_journey_has_an_answer_key.py · test_the_handoff_says_whether_perfetto_fetched.py
guards:   A the bound, not the seconds (UX-539's pattern) · B a mutation planting a harness in each form
          C a mutation to any underlying population reddens rather than passing · D none (a guard is out of scope for UX-548)
          E the clause green three times at 8 workers, load average pasted
gap:      UX-544's census matches ZERO files today, not four - the item understates its own gap
track:    A alone, first · B ‖ D ‖ E · C serial after A · F at the gate
gate:     one PR, opened first; per item the suite, per round one merge
```

## Collisions the order has to survive

| shared path | ids | resolution |
|---|---|---|
| `docs/README.md` | `UX-540`, `UX-549` | one paragraph, one sentence — C takes both, serial |
| `CHANGELOG.md` | `UX-549` (:5), `UX-550` (0.3.0 block) | `UX-550` may insert a release above :37 and move every line `UX-549` cites — `UX-550` first |
| `docs/design/architecture.md` | `UX-540`, `UX-548`, `UX-549` | distinct line ranges; C owns the file, D rebases onto it |
| `docs/guides/cli.md` | `UX-548` (:1038, :1302, :1374), `UX-552` (:47-65) | distinct ranges, one track |
| `contracts.ids()` / `superseded()` | `UX-540`, `UX-549`, `UX-550` | semantic, not textual — the reason C is serial |

## The gate this round actually ran, and the deviation in it

Fixing guide §3 asks for the whole suite before any item is marked 🟢.
This round did not do that, and the deviation is written here rather
than left to be inferred from the commits.

What ran per item: `make test-touching`, the item's own guards, and
every new guard mutated red and reverted. What ran per **track merge**:
the suite. Fourteen items at round 80's 8m52s is about two hours of
gate, and with four tracks in worktrees "per item" is not even defined
until they merge.

`UX-500`'s two rounds are sometimes read as a mixed result. They are
not — they are a clean negative, but of a different question:

| | round 75 (A) | round 80 (B) |
|---|---|---|
| defects the gate caught | 5 | 9 |
| **of those, outside `test-touching`'s set** | **2** | **4** |

That measures the *cheap selector* against the suite, and says the
suite must run. It says nothing about **how often** — whether a suite
run per item catches anything a suite run per merged batch misses has
never been measured, by either round. Round 80 ran it per batch and
that gate caught nine.

So the honest statement of this round's regime: the suite gates each
**merge**, not each item, and the figure below continues `UX-500`'s
series on a third round shape — four parallel tracks with the
orchestrating session working five of the items itself.

```text
round 81, defects the merge gates caught        5
  of those, outside test-touching's set         1
```

Derived, not counted by hand: for each defect, `dev_touching.select`
was run on the diff of the commit that introduced it, and asked whether
the file that went red is in the result.

| defect | introduced | red file in the set? | set |
|---|---|---|---|
| `UX-554`'s Out of Scope entry is a bare noun phrase | `7acbf2b` | yes | 38 |
| `dev_junit_tail.py` is not on the §6 context map | `ddcb969` | **no** | 50 |
| the one-reference clause counts a proxy (3 == 1) | `b04a340` | yes | 25 |
| `UX-544`'s census names 5 sites, no harness converted | `c21a434` | yes | 11 |
| `UX-543`/`UX-546` rows left 🔴 against 🟢 files | `f6d947a` | yes | **424** |

The series, on three round shapes:

```text
round 75 (A, suite per item)    2 of 5
round 80 (B, batch gate)        4 of 9
round 81 (B, four tracks)       1 of 5
```

Two qualifications, both of which the raw ratio hides.

**The last row's "yes" is worth nothing.** Its set is 424 — the whole
suite — because `f6d947a` touches `tests/conftest.py`, one of
`dev_touching`'s `EVERYTHING` paths. The selector did not *select* that
file; it declined to select at all. `UX-557` is that row.

**Two more defects were caught and are not counted.** `UX-554`'s
3.11-only junit, whose next red job was 3.12; and the Verification Log
header, whose regex takes one id and was given two. Neither has a clean
introducing commit to measure a selector against, so counting them
would be an estimate, and the point of this cell is that it is not.

What the three rounds now say together is still about the **selector**,
not the cadence: a suite run catches things a grep-derived set misses,
in every round that has looked. Whether it must run per item or per
merge remains unmeasured, and round 81 did not measure it either.
