# UX-1301: four capture flags appear in no `--help`, under a heading that says they do

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_capture_run_help_lists_the_translated_flags.py`

## Motivation

`bga/cli.py:3600-3611` strips `--jobserver-auth-override`,
`--lto-cap`, `--wrapper-dir` and `--wrapper-dir-mode` out of argv before
the tracer's argparse prints `--help`, so none of the four is in it;
cli.md lists them under "Flags reachable only from `--help`". The help
that is printed is stale too: `--jobserver-auth` says `auto` picks
`fifo:` from Make 4.4, while `tools/jobserver/ledger.py:183` resolves
`auto` to `fd` always (`UX-876`), and `--jobserver N` hides `auto|off`.

```text
$ bga capture run --help | grep -cE 'auth-override|lto-cap|wrapper-dir'
0
$ bga capture run --help | grep -A2 'jobserver-auth {'
UX-841: the --jobserver-auth style; auto picks fifo:
from GNU Make 4.4, fd below, by the host's own `make
--version`.
$ sed -n 1224p docs/guides/cli.md
### Flags reachable only from `--help`
```

## Decomposition

Input classes: each of the four translated flags (`--jobserver-auth-override`, `--lto-cap`, `--wrapper-dir`, `--wrapper-dir-mode`); `--jobserver`'s `auto|N|off`; `--jobserver-auth`'s `auto`. Journey: `bga capture run --help`, then the flag on a capture.

## Required Fix

`bga capture run --help` prints the four translated flags (an epilog
or argparse entries the translators consume) and `--jobserver`'s
`auto|N|off`; the `--jobserver-auth` help states `auto` is `fd`; cli.md's
heading names what the list really is.

**Decision:** an epilog `bga/cli.py` prints after the tracer's own help
when `capture run --help` is asked before any `--`
(`CAPTURE_RUN_BGA_FLAGS`, `capture_run_epilog`); the tracer's
`--jobserver` and `--jobserver-auth` help lines carry `auto|N|off` and
`auto resolves to fd`. The heading becomes "What each flag does, in
full"; both links to the old anchor move. `test_help_is_short.py`'s
`capture run` cap is `CAP + 6`, the epilog's own lines.

## Out of Scope

`bga snapshot`'s missing flags (`UX-1302`).

## Acceptance Test

A guard compares the translators' flag set with `bga capture run
--help` and reddens when one is missing; the help's `auto` sentence
matches `jobserver_auth_style` (`tools/jobserver/ledger.py:181`). Reading taken in this container.

## Outcome

## Outcome (round 168, 2026-10-03) — 🟢 Done

**Premise:** held — the four translated flags were in no `--help`, and
`--jobserver-auth`'s help named a `make --version` probe `UX-876` removed.

### The gap, measured

```text
$ bga capture run --help | grep -cE 'auth-override|lto-cap|wrapper-dir'   # HEAD 9dd99dc0
0
$ bga capture run --help | grep -cE 'auto resolves to fd|auto\|N\|off'
0
```

None of the four flags `_translate_capture_*` strip, nor `auto|N|off`,
nor what `auto` resolves to, was in the help.

### After

```text
$ bga capture run --help | grep -cE 'auth-override|lto-cap|wrapper-dir'
4
$ bga capture run --help | grep -E 'auth-override|lto-cap|wrapper-dir|auto\|N\|off|auto resolves'
                        `bga` also takes auto|N|off (UX-851).
                        UX-876: make's --jobserver-auth style; auto resolves
  --jobserver-auth-override 'STYLE:GLOB ...'  per-element fd|fifo|off|flto, repeatable
  --lto-cap N  the flto shim's static -flto=N (default nproc)
  --wrapper-dir PATH  an operator's own wrapper directory
  --wrapper-dir-mode augment|replace  ahead of the shipped shims, or instead
$ bga capture run --help | wc -l
72
```

The guard reads the flag set from the `_translate_capture_*` sources
(`tok == '--…'`), so a fifth translated flag reddens it until the epilog
names it.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| A1 | drop `--lto-cap` from `CAPTURE_RUN_BGA_FLAGS` | `test_every_translated_flag_is_in_the_help`, 1 failed 4 passed |
| A2 | a fifth translated flag `--new-flag` in `_translate_capture_lto_cap` | `test_every_translated_flag_is_in_the_help`, 1 failed 4 passed |
| A3 | epilog never printed | `test_every_translated_flag_is_in_the_help`, 1 failed 4 passed |
| A4 | tracer `--jobserver` help without `auto\|N\|off` | `test_the_jobserver_line_shows_auto_n_off`, 1 failed 4 passed |
| A5 | `jobserver_auth_style('auto')` returns `fifo` | `test_the_auth_help_says_what_auto_resolves_to`, 1 failed 4 passed |
| A6 | help detection reads past `--` | `test_a_help_after_the_separator_is_the_wrapped_command_s`, 1 failed 4 passed |

Reverted from a copy: 5 passed.

### Deviation from the Required Fix

None. The new guard names `bga.cli`: `test_the_loop_stays_fast.py`'s
selector `max` ceiling 199 -> 200 (measured 200 over 819 files).

```text
$ PYTEST_XDIST= python3 -m pytest -q -p no:randomly tests/unit/test_capture_run_help_lists_the_translated_flags.py tests/unit/test_help_is_short.py
111 passed in 1.30s
$ make lint   # ruff check, ruff format --check, dev_baseline --check, PyMarkdown: clean
```
