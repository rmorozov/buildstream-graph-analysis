# UX-1384: `make lock` resolves on the Python the lock check compiles on

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** `retro-2026-10-26.md` proposal 2; Ruslan filed it on the decision card, 2026-11-05 19:54 UTC | **Serves:** anyone who regenerates `requirements.lock` | **Topic:** guards | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_make_lock_resolves_on_the_check_s_python.py`

## Motivation

`make lock` runs `uv pip compile` on the host's Python, while
`quality.yml` compiles on `3.12`. A 3.13 resolve drops referencing's
`typing-extensions` edge, so `#332` needed a second commit (`42f5e878`)
and `#334` needed `--python-version 3.12` by hand. Since `UX-1379` the
floor is 3.11, so "the floor" and "the check's Python" are no longer
one number.

## Required Fix

`make lock` passes `--python-version` read from the one place
`quality.yml`'s lock check takes it, so a lock written on any host
equals what the check compiles.

## Out of Scope

Which Python the check itself runs on.

## Acceptance Test

`make lock` on a 3.13 host leaves `requirements.lock` byte-identical to
the check's compile; a guard reddens when the two versions differ.

## Decision

The Makefile is the one place: `LOCK_PYTHON := 3.12` and one
`LOCK_COMPILE` (`--python-version $(LOCK_PYTHON) --custom-compile-command
"make lock"`) behind `lock` (`--upgrade`), `lock-sync` (no upgrade: only
what `pyproject.toml` moved moves) and `lock-check` (seeded, `UX-1128`).
`quality.yml`'s step runs `make lock-check`; the fixed header makes the
diff whole-file, so the `grep -v '^#'` filter that kept the indented
`#   referencing` line as content is gone.

## Outcome

Gap, this container (Python 3.13.18, uv 0.11.32), `main` at `0aa392cf`:

```text
$ uv pip compile pyproject.toml --extra dev -q -o <seeded copy>   # the old `make lock`, minus --upgrade
$ diff <(grep -v '^#' requirements.lock) <(grep -v '^#' <copy>)
105d104
<     #   referencing
```

Close: `make lock-sync` on the same 3.13 host changes line 2 only
(`#    uv pip compile ...` -> `#    make lock`), then `make lock-check` -> rc 0.
`python3 -m pytest -q -p no:xdist tests/unit/test_make_lock_resolves_on_the_check_s_python.py` -> 4 passed.

| mutation | count |
|---|---|
| M1 `--python-version $(LOCK_PYTHON)` dropped from `LOCK_COMPILE` | 1 failed, 3 passed |
| M2 quality.yml compiles inline again | 1 failed, 3 passed |
| M3 `LOCK_PYTHON := 3.13` (two versions) | 1 failed, 3 passed |
| M4 `lock-sync` with its own `uv pip compile` | 1 failed, 3 passed |
| M5 the lock's old header restored | 1 failed, 3 passed |
| reverted | 4 passed |

`test_the_gate_only_shelf_is_on_github.py`'s seeded-lock check now reads
the `lock-check` recipe; 9 passed.

Owner review of #352: the fixed `/tmp/bga-lock-check.lock` let two checkouts diff each other's
compile. Scratch is now `$(CURDIR)/.lock-check.lock`, gitignored, so it is per checkout, not per
invocation: a recipe `rm` is refused in this session, and one checkout runs one `make lock-check`
at a time. `make lock-check` -> rc 0; the guard file -> 5 passed.

| mutation | count |
|---|---|
| M6 `LOCK_SCRATCH := /tmp/bga-lock-check.lock` | 1 failed, 4 passed |
| M7 the recipe's `cp` and compile name `/tmp/x.lock` | 1 failed, 4 passed |
| reverted | 5 passed |

Owner re-review of #352 (head `d3261bd0`): per checkout still let two runs in one checkout pass a
stale lock, and the unquoted absolute path split on a space. `make lock-check` is now
`tools/dev_lock_check.py $(LOCK_COMPILE)`: seed, compile, compare in one `TemporaryDirectory`,
which Python removes, so no recipe `rm` and no shell path. Guards run the real recipe in a
`BGA work` checkout against a stub compile: seeded first, and a stale run paused 1.5 s while a
fresh one completes in the same checkout. `make lock-check` -> rc 0; the file -> 6 passed.

| mutation | count |
|---|---|
| M8 the tool compiles into a fixed `REPO/.lock-check.lock` | 1 failed, 5 passed |
| M9 the seed copy dropped | 2 failed, 4 passed |
| M10 the old `cp`/`-o`/`diff` recipe on `$(CURDIR)/.lock-check.lock` | 2 failed, 4 passed |
| reverted | 6 passed |
