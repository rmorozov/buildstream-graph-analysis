# UX-976: the toolchain closure is 35 store paths, and the examples README counts the two make pins into it

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-925 | **Blocks:** — | **Found by:** architecture review 26 (2026-09-23) — `nix_closure --plan` over `nix_toolchain.roots()` totals 35, and `examples/README.md:117` says 37 | **Serves:** whoever sizes the examples' download from the README | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

`examples/README.md:117`: "gcc, binutils and cmake are fetched from
`cache.nixos.org` as one 37-path closure". The closure of those three
roots, walked by the tool that stages it:

```text
$ python3 -m tools.nix_closure --plan \
    --root /nix/store/ipr6y28viyqkhkg58rdvy27m01q5j5nh-gcc-14.3.0 \
    --root /nix/store/i7mdvmliqcb5lz0nqija8rq55vws6gi8-binutils-2.44 \
    --root /nix/store/i5zf2arkflazjnxv2y46fmhyfwzl5hdy-cmake-4.1.2 \
    --cache-dir <scratch>/narcache <scratch>/dest | tail -1
#  35 paths  438654496 bytes unpacked
```

The roots are `nix_toolchain.roots()` verbatim. The other two are the
`make` pins, `tools/nix_store_fetch.py:48` and `:62` (`gnumake-4.4.1`,
`gnumake-4.2.1`), which are single NARs outside that closure:
`grep -c gnumake` over the plan prints 0. 35 + 2 = 37 is the staged
tree's store paths - the figure `UX-925`'s Outcome measured with
`examples/stage_cpp_toolchain.sh`, and correct there.

The README moved it onto the toolchain. No guard reads the sentence.
The records carrying `37 paths` (`closed.md`'s `UX-925` row,
`round-137.md`, `directions.md`'s round-137 row) are dated and describe
the staged tree, so they stay.

## Required Fix

Say which population the figure counts: 35 for the toolchain closure,
or 37 for the staged tree with the two `make` pins named. Derive it
from `nix_closure --plan`'s total line, the only source that prints
it.

## Out of Scope

The dated records above. The `420 MiB` beside it (438654496 bytes is
418 MiB for the 35; the make pins cover the rest). A guard that fetches
narinfos.

## Acceptance Test

`grep -n "37-path" examples/README.md` prints nothing, and the sentence
that replaces it names the population it counts.

## Outcome
