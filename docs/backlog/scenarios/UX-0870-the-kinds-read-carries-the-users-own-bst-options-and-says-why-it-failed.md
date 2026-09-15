# UX-870: the kinds read carries the user's own bst options and says why it failed

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-843 | **Found by:** round 121, the user (a real project under a junction, GNU Make 4.4 on the host) | **Serves:** R2 (every element joins by its kind on a project built with -o and --config) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`read_element_kinds_for_jobserver` runs `bst show --format '%{name}
%{kind}' <target>` with only `cmd[0]` and one target: every other token
of the user's own command - `-o` project options, `--config`,
`--directory`, a second target - is dropped, and a build with no
explicit target (project.conf's default) never runs the read at all.
A failing `bst show` returns `None` with its stderr discarded, and the
capture keeps no record of which happened; the user saw "bst show gave
no element kinds" and every decision read `unknown_kind`.

## Required Fix

`tools/bst_native_build_tracer.py`: the read reuses the global
options that precede the subcommand in the user's command and `-o`,
`--config`, `--directory` wherever they sit, and with no target runs
`bst show` on the project's default target (no target argument); on
failure it writes `kinds_read.json` beside `element_kinds.json` in the
bind dir with the argv, the exit status and stderr's tail, and the
warning names the reason (no target, exit N, no lines parsed).

## Decomposition

Input classes: options before the subcommand, after it, none; a
target, none; exit 0, exit N, empty stdout; the journey it extends is
`UX-843`'s per-kind join on a real project's command line.

## Out of Scope

Reading kinds from anything but `bst show`.

## Acceptance Test

`tests/unit/test_the_kinds_read_carries_the_options.py`: a fake `bst`
on `PATH` records its argv - `cmd = [bst, "-o", "arch", "x86_64",
"--config", "c.yml", "build", "t.bst"]` reaches it with the options
and the target; no target reaches it with none; a non-zero exit writes
`kinds_read.json` with the status and the warning names it; mutation:
drop the option forwarding - red.
