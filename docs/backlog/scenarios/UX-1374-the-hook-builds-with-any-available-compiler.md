# UX-1374: the hook and spine build with any available C compiler, `$CC` first

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1373 | **Found by:** Ruslan, 2026-11-02: "add ability use any available compiler - like clang not only gcc" | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_the_hook_compiles_with_any_available_compiler.py`, `tests/unit/test_doctor.py`

## Motivation

`c_compiler` took `cc`, else `gcc`, and ignored `$CC`. A host with clang
alone, or a team that sets `CC=ccache clang`, read "no C compiler" from
`bga doctor` and from the capture, and the `BGA_HOOK=prebuilt` wheel
build (`UX-1373`) inherited the same choice.

## Decomposition

Input classes: `$CC` a name, a path, a word list, set but missing;
unset with `cc`, only `gcc`, only `clang`, none. Surfaces: the capture,
`bga doctor`, the prebuilt wheel build.

## Required Fix

`prebuilt.compiler()` is the one choice: `$CC` split like a shell word
list, else the first of `cc`, `gcc`, `clang` on PATH. A `$CC` that does
not resolve fails naming it and never falls back. `c_compiler`, doctor
and `setup.py` call it; the argv is a list throughout.

## Out of Scope

Per-compiler flags: both builds use flags clang and gcc share.

## Acceptance Test

Container: PATH holding only `clang` and `ld` builds the hook and the
static spine, doctor reads `ok` naming clang, a `CC=clang` prebuilt
wheel stamps clang; `CC=ccache` with no ccache fails naming `CC`.

## Outcome

**Premise:** held.

### The gap, measured

At `4cc605bc` (UX-1373), doctor under a PATH of `clang`, `ld`, `python3`:

```text
fail no C compiler (cc/gcc) found on PATH - required to build the LD_PRELOAD hook
CC=ccache: fail no C compiler (cc/gcc) found on PATH - required to build the LD_PRELOAD hook
```

### The close, measured

Same PATH, this tree:

```text
ok C compiler at …/onlyclang/clang builds the hook and links static
CC=ccache: fail CC='ccache' is not on PATH - required to build the LD_PRELOAD hook
```

The guard with `test_doctor.py`: `51 passed, 8 skipped`; the new file
alone `8 passed in 9.76s`.

| mutation | reddened | run |
|---|---|---|
| N1 `c_compiler` back to `cc` or `gcc` | clang alone on PATH, doctor names clang, the capture's reason, doctor reads the capture's predicate | 4 failed |
| N2 a missing `$CC` falls back | a named CC does not fall back, the capture's reason | 2 failed |
| N3 the wheel build ignores `$CC` | a `CC=clang` prebuilt wheel stamps clang | 1 failed |
| N4 `$CC` not split | split like a shell word list | 1 failed |
| N5 clang not a candidate | first candidate wins, none names every candidate, clang alone on PATH | 3 failed |
| reverted | — | 51 passed, 8 skipped |

### Deviation

`test_doctor.py`'s UX-143 clause grepped `c_compiler` for
`shutil.which("…")` literals; it now asserts `c_compiler` calls
`prebuilt.compiler()` and reads `CANDIDATES`, the predicate itself.
