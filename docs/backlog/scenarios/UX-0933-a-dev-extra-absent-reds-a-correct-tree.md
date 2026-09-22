# UX-933: the `zstd` clauses fail where every other optional prerequisite skips, so a tree without the extra reads as a broken one

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-927 | **Blocks:** — | **Found by:** the sequencing thread, reading `UX-927`'s guard against `UX-213`'s rule | **Serves:** anyone running the suite from a plain `pip install -e .`, and the census that has to believe a skip | **Topic:** guards | **Area:** unassigned | **Shape:** bounded

## Motivation

`UX-927` added a guard whose `zstd` clauses import `zstandard`
directly. `zstandard` is in the `dev` and `nix` extras, so the clauses
run everywhere the extras are installed — and **fail**, rather than
skip, everywhere they are not:

```text
$ PYTHONPATH=<a dir whose zstandard.py raises ImportError> \
    python3 -m pytest tests/unit/test_the_staged_closure_is_complete.py
E   ModuleNotFoundError: No module named 'zstandard'
```

Every other environment-dependent file in this tree skips on a missing
prerequisite — `UX-213`'s rule, and `jsonschema`, `buildstream`,
`trace_processor_shell` and the real-capture arms all follow it. A
clause that fails instead reds a tree that is not broken, which is the
shape this repository keeps filing rows about from the other side.

**Why the original choice was not simply wrong.** `conftest.py`'s own
argument is that a skip is invisible in a pass count, and `UX-197` has
CI set `BGA_EXPECT_DEV` so a missing dev extra *fails* rather than
skipping. Failing unconditionally gets that half right and the other
half wrong. The resolution is the one already in the tree for
`jsonschema` since `UX-190`: **skip on absence, and carry a canary that
reds wherever the environment claims the extras.**

`conftest.py` names the gap this leaves in so many words — the canary
"knows about `jsonschema` only". This adds the second one rather than
closing that permanently; see Out of Scope.

## Required Fix

The `zstd` clauses skip on a missing `zstandard`, under a module-level
`skipif` with a literal reason — a marker, not a module-scope
`importorskip`, which round 21's seam 6 banned.

The reason is declared in `conftest.KNOWN_SKIP_REASONS`, because
`tests/unit/test_every_skip_reason_is_declared.py` reads reasons out of
the **source** rather than from skips that fired: the machine that
writes the clause is the machine that has the extra, so a reason
declared nowhere would be found by CI and not by its author.

A canary beside the clauses asserts `zstandard` imports wherever
`BGA_EXPECT_DEV` is set, so the skip cannot go quiet in CI.

The parametrized round-trip splits: `none` and `xz` are stdlib and keep
running everywhere, and only the `zstd` arm carries the marker. A
parametrization where one case skips and two do not is harder to read
in a summary than two clauses named for what they need.

**A note on the header.** This row's `**Area:**` is `unassigned`
because the §6 vocabulary `dev_close_task.py` derives is `bga`,
`tools`, `bga/viewer` and their subdirectories — there is no `tests`
area, though the whole change lives under `tests/`. Declaring one is a
row of its own, not a thing to invent in a header.

## Out of Scope

Generalising the canary to every distribution in the `dev` extra,
which is what `conftest.py`'s "knows about `jsonschema` only" points
at. It needs a distribution-name to import-name map that this
repository does not have — `pytest-cov`, `pymarkdownlnt` and
`pytest-xdist` all differ from their import names, and `ruff` and
`pyright` are binaries with no import at all. Worth a row; it is not
this one, and doing it badly would trade a narrow gap for a wrong list.

Moving `zstandard` out of `dev` into `nix` alone. CI installs `dev`,
and a guard that never runs in CI is the defect `UX-197` exists for.

## Acceptance Test

With `zstandard` absent, `tests/unit/test_the_staged_closure_is_complete.py`
skips its `zstd` clauses with the declared reason and the file stays
green; with `zstandard` absent **and** `BGA_EXPECT_DEV` set, the canary
fails and names the extra.

`tests/unit/test_every_skip_reason_is_declared.py` passes, which is the
claim that the new reason was declared rather than discovered.

## Outcome (round 136, 2026-09-22) — 🟢 Done

**Premise:** held — the clauses failed on absence where the rest of the
tree skips, and the fix had to keep the failure where it was right.

### The gap, measured

`zstandard` blocked by a stub on `PYTHONPATH` that raises `ImportError`:

```text
$ PYTHONPATH=<stub> python3 -m pytest tests/unit/test_the_staged_closure_is_complete.py
E   ModuleNotFoundError: No module named 'zstandard'
```

A tree that never claimed the extra read as a broken one. `UX-213`'s
rule and four existing prerequisites (`jsonschema`, `buildstream`,
`trace_processor_shell`, the real-capture arms) all skip instead.

### After

Both arms, same stub:

```text
$ PYTHONPATH=<stub> python3 -m pytest ... -rs
SKIPPED [1] ...:246: zstandard is not installed - `pip install -e '.[dev]'`
SKIPPED [1] ...:261: zstandard is not installed - `pip install -e '.[dev]'`
SKIPPED [1] ...:275: not a dev environment by its own account (BGA_EXPECT_DEV is unset)
18 passed, 3 skipped

$ PYTHONPATH=<stub> BGA_EXPECT_DEV=1 python3 -m pytest ...
E   AssertionError: BGA_EXPECT_DEV is set, so this environment claims the
    dev extras, but `zstandard` is missing and the `zstd` clauses here
    just skipped.
1 failed, 18 passed, 2 skipped
```

Green where nothing was claimed, red where it was. That pair is the
whole row: skipping alone would have traded a false red for a silence,
which is what `conftest.py` was built to refuse.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| C1 | the canary drops its `BGA_EXPECT_DEV` assertion | arm 2 goes green with `zstandard` absent — the silence the census exists to catch |
| C2 | the reason is removed from `KNOWN_SKIP_REASONS` | `test_every_skip_reason_is_declared` |

C2 is the one worth recording. The declaration guard reads reasons out
of the **source**, not from skips that fired, precisely because the
machine that writes a clause is the machine that has the extra — so an
undeclared reason is found by CI and never by its author. It reddens
here on a machine where the skip never fires.

### Deviation from the Required Fix

None. The general form — a canary over every distribution in the `dev`
extra, which `conftest.py` notes "knows about `jsonschema` only" — is
recorded in Out of Scope with the reason it is not free: no
distribution-name to import-name map exists, and `ruff` and `pyright`
have no import at all.

```text
$ make lint
All checks passed!
$ make test
9214 passed, 181 skipped, 1 warning in 309.27s (0:05:09)
```
