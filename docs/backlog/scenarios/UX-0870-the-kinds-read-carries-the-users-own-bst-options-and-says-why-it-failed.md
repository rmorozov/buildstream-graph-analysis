# UX-870: the kinds read carries the user's own bst options and says why it failed

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-843 | **Found by:** round 121, the user (a real project under a junction, GNU Make 4.4 on the host) | **Serves:** R2 (every element joins by its kind on a project built with -o and --config) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

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

## Outcome

**Gap measured.** Pre-fix, `read_element_kinds_for_jobserver(project_dir,
["bst", "-o", "arch", "x86_64", "--config", "c.yml", "build", "t.bst"])`
ran `[cmd[0], "show", "--format", "%{name} %{kind}", "t.bst"]` - `-o
arch x86_64 --config c.yml` dropped - and a `build` with no positional
target returned `None` before `subprocess.run` ever ran, with no record
of either.

**Close measured.** Same call now composes `[cmd[0], "-o", "arch",
"x86_64", "--config", "c.yml", "show", "--format", "%{name} %{kind}",
"t.bst"]` (`_bst_global_options`, arity read off the installed
`buildstream/_frontend/cli.py`'s `cli` group); no target runs `show`
with none; a subcommand's own trailing options (`--retry-failed`) do
not leak in. `tests/unit/test_the_kinds_read_carries_the_options.py`:
`10 passed in 0.34s` (fresh fake-`bst` fixture, no real `bst`/`bwrap`).
`tests/unit/test_native_build_tracer.py`: `47 passed, 1 skipped`.
`make test-touching` (2925 items, direct `pytest -n 2` split): `2887
passed, 36 skipped` first pass, 2 failed on `fixing-guide.md`'s stale
touching-spread figure (552 -> 553 test files, the new file) -
`python3 tools/dev_touching.py --spread --write` then
`tests/unit/test_the_cost_row_is_derived_from_the_selector.py`: `11
passed`. `python3 tools/dev_close_task.py --check`: `0 problem(s) over
10 propert(y/ies), 869 backlog row(s)`. `python3 tools/dev_sizes.py
--check` (post `--adopt --force`): `sizes ok`. `python3
tools/dev_baseline.py --check`: `clean` (no new finding; the `bst
show` `subprocess.run` call stays inside UX-843's forced S603 rows).
`python3 -m pymarkdown --config .pymarkdown.json scan` on
`docs/guides/cli.md`, `docs/contributing/fixing-guide.md`, this file:
no output (clean).

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| drop `global_opts` from the composed `argv` | `test_global_options_and_their_values_precede_show` | 1 failed, 9 passed -> reverted, 10/10 |
| drop the `kinds_read.json` write in `_write_kinds_read` | `test_a_nonzero_exit_writes_the_reason_and_stderr_tail`, `test_a_success_file_records_argv_and_count` | 2 failed, 8 passed -> reverted, 10/10 |

Deviation: none from the Required Fix. One scope note - `_write_kinds_read`
was split out of `run_traced_build` (not named in the Decomposition) so
the write+warn pairing is unit-testable without a real sandbox; the
warning's print call moved from `main()` (before `bind_dir` exists) into
`run_traced_build` (where the file's real path is known), so it can name
the file. `read_element_kinds_for_jobserver` returns `(kinds,
diagnostic)` rather than `Optional[dict]` - no other caller existed.

**Deviation (merge):** the verifier read the arity table complete
against the installed `cli` group (BuildStream 2.8.0) but found only
`-o` and `--config` exercised - dropping `--directory` passed the whole
file. At merge a guard derives its cases from the installed group's
own `params` (every valued option, its `nargs`); mutation: drop
`--directory` from the set - `1 failed`, naming it. `bst build --deps
all t.bst` still resolves `all` as the target through `_cmd_target`
(`UX-842`); this row makes that failure visible in `kinds_read.json`
and `UX-873` is filed for the arity. `timeout`/`oserror` reasons stay
unguarded by a dedicated case.
