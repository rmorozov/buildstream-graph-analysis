# UX-1301: four capture flags appear in no `--help`, under a heading that says they do

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Out of Scope

`bga snapshot`'s missing flags (`UX-1302`).

## Acceptance Test

A guard compares the translators' flag set with `bga capture run
--help` and reddens when one is missing; the help's `auto` sentence
matches `jobserver_auth_style` (`tools/jobserver/ledger.py:181`). Reading taken in this container.

## Outcome
