# Round 136 — three rows, three threads, and a document none of them wrote

Run on 2026-09-22 from `6d78912d`. Three rows closed — `UX-924`,
`UX-927`, `UX-930` — in three concurrent threads, landing as `#262`,
`#260` (`cbcdae85`) and `#261` (`3fa407a0`).

**This document is written in round 137, from the three task files'
Outcomes and the ledger's two round-136 rows, not from a transcript.**
No thread wrote it at the time, which is `UX-926`'s shape exactly: the
register derives a round from its records, so a round that closes in
parallel has no single session holding the obligation, and the guard
that demands a document only fires once a *later* round takes the
highest number. Round 137's close is what made this one visible.
Rounds 132 and 133 remain undocumented and unwaived.

```text
closed   UX-924   the adopt route feeds the committed median back to itself
closed   UX-927   a pin is one NAR, so a staged compiler reaches outside itself
closed   UX-930   the toolchain's two parameters are assumed, not read back
```

## `UX-924` — a window that adopts its own carried copy

`adopt` took `candidate["files"]`, already the `median_low` of that
candidate's own samples, so a flat window fed the committed value back
onto itself and the document learned nothing from the run:

```text
ref    files 6.47  samples [6.48, 6.47, 6.47, 6.47, 6.47]
cand   files 6.28  samples [6.28, 6.28, 6.28, 6.28, 13.28]
adopt  files 6.47  samples [6.47, 6.47, 6.47, 6.47, 6.47]      # before
adopt  files 6.47  samples [6.47, 6.47, 6.47, 6.47, 13.67]     # after
```

538 of 561 entries held a full window and 367 of those were flat. The
fix takes `readings_of(candidate)` — the newest sample, that run's own
seconds, divided by the run's shift like every adopted row. Replayed
over the 367 flat windows, the median moves at adoption 3 for 258, at
6 for 7, and never for 102 where the reading already equals the
committed value. Three mutations, all red: the defect itself reddened
3 of 5 clauses. The shift stays median-against-median (0.9712 against
0.9713 over ~500 ratios, 0.01 %), because `IMAGE_BAND`'s refusal is
calibrated on the first.

## `UX-927` — a pin is a closure, not a NAR

The single-NAR pin staged **1 store path of 5** for `make`, and would
have staged 1 of 15 for gcc. `make` worked anyway only because
`stage_interpreter_link` symlinked into a host-staged glibc; a
compiler has no such single reference. `tools/nix_closure.py` walks
the narinfos transitively, stages every path at its own
`/nix/store/<hash>`, and reports any reference the tree does not
carry — a completeness check that needs neither Nix nor a sandbox.

```text
5 paths, 1.820s;  nix_closure --check: zstd backend zstandard, exit 0
unshare -r -m + bind mount, on a host with no /nix at all: GNU Make 4.4.1
```

Two readings decided the shape. All 15 of gcc's paths arrive `zstd`,
stdlib `lzma` stages none of them and `nar/<narhash>.nar` is 404, so
the decompressor cannot be dodged — `zstd` became a declared
dependency rather than ~800 lines of vendored bit-level decoding whose
failure mode is a corrupt sysroot. And the gate moved to `NarHash`:
`glibc-2.40-224` arrives recompressed, 9,099,653 bytes against a
declared 9,096,823 with `FileHash` disagreeing while `NarHash` and
`NarSize` are exact, so gating on `FileHash` would refuse a correct
store path over its wrapper. Six mutations, all red.

## `UX-930` — ask the driver, do not assume

`-B` at a directory with no `cc1` compiles the whole example against
the host's compiler at **exit 0 and 0 bytes of stderr**, where
`--sysroot` at least fails the `#include`. `tools/toolchain_params.py`
declares seven file classes and asks the driver where each really came
from. Two numbers came out of it: `-B` is **three** directories rather
than one — the libexec prefix alone leaves five of seven classes on
the host, and adding the gcc libdir still leaves the start files — and
six of seven carry, with the C++ headers declared in `UNREADABLE_HERE`
rather than excused silently. Seven mutations, all red.

Its own half-falsification of `UX-925` is the finding that matters:
`make_relative_prefix` **does** relocate a whole-tree move through
`argv[0]`, so a copied tree's driver finds its own `cc1`, `libgcc` and
internal headers. Only the target's half stays absolute. Round 137
takes the rest of that title down.

## What the round cost twice, in the same shape

Two of the three rows were bitten by a fixture that could build the
wrong tree without saying so. `UX-930`'s clone does `cp -al` and falls
back to `cp -a`, and a cross-device `cp -al` **creates the destination
and then fails per file** — so the retry copied *into* the leftover
directory, nested the tree one level down, and every glob returned
`[]`. Green wherever `/usr` and `tmp_path` share a filesystem, red on
all four CI Pythons: 7 failed before `--basetemp=/dev/shm` forced it,
19 pass after. A relative `dest` produced the same class of silence
from the other side — relative `-B` flags whose answers sat outside
the absolute tree and read as the host's, which is this row's own
failure shape from the inside.

`UX-924` carries the third: `design-review` was routed to and not run,
because that skill's protocol opens on a served page this diff never
touches. A reader pass ran instead and took two corrections; the seam
is filed as `UX-928`.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| self-review | sonnet | `UX-924` close | 110k | 30 | 6.2 m | its first `git diff origin/main -- .` silently dropped a changed file and cost a re-read of the whole diff |
| researcher | sonnet | `UX-924`'s three prose surfaces, in place of the `design-review` the route asks for | 61k | 14 | 3.6 m | hand-simulating five adoptions of a window to check the three/five/two counts, which no comment or guard states directly |

One Important finding and one nit, both acted on: the Outcome's
`make test` line was a placeholder while both status markers already
read 🟢, and the adopt-commit cadence was uncited. `UX-927` and
`UX-930` launched none — both shapes derive `bounded` and each
session took its own row in context, so the ledger has no row to
carry for them.
