# UX-191: tab completion without a rewrite

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-158 (the help surface completion complements), UX-126 (the alias grammar worth completing)

## Motivation

Field feedback: *"maybe it's good idea to bring autocompletion for
command line... it looks like migration to python3 click from native
argparse can simplify support of such scenario. it will greatly
improve UX on commands like bga cache-trend."* The need is real —
fifteen subcommands, sticky flags, `@`-aliases and run-directory
arguments are exactly what completion is for. The migration is not:
**`argcomplete` provides shell completion for argparse programs as
they stand** — one `PYTHON_ARGCOMPLETE_OK` marker, one
`argcomplete.autocomplete(parser)` call, an optional dependency — while
a click rewrite would touch every subcommand, re-litigate UX-158's
help formatting (click renders its own), and re-risk the CompactHelp
work for no user-visible gain beyond what argcomplete already gives.
Decision, with the trade-off recorded: argcomplete, and click stays a
non-goal unless argcomplete proves insufficient in use.

The completions that earn their keep:

- subcommand names and flags everywhere (argcomplete gives these
  free);
- `@last`/`@prev`/`@<stamp>` wherever a run ref is accepted — a
  custom completer over `run_store.list_snapshots`, which makes
  `bga cache-trend @<TAB>` and `bga compare @<TAB>` the experience
  the feedback asked for;
- element names for `bga blast` (from the project's element files);
- `--trace-spine={off,on,auto}` and friends from their choices
  (free).

## Required Fix

Wire `argcomplete` behind an optional extra (`pip install
bga[completion]` or plain dependency if the wheel-size cost is nil);
register the custom completers above; document activation
(`eval "$(register-python-argcomplete bga)"` for bash/zsh, the
fish equivalent) in README's install section — three lines, per the
concision budget; `bga doctor` mentions completion only if trivially
checkable, else nothing.

## Out of Scope

- A click migration (recorded as considered and declined, with the
  reasons above — revisit only if argcomplete cannot complete
  something users need).
- Completing remote refs or urls (no source of truth to complete
  from).

## Acceptance Test

With argcomplete's test harness (it ships one:
`argcomplete.autocomplete` under `_ARGCOMPLETE` env), completions for
`bga <TAB>` include the subcommands, `bga compare @<TAB>` lists the
store's snapshots on a fixture project, and `bga blast <TAB>` lists
element names; a shell without activation sees zero behavior change
(the marker line is inert); help lines and `--help` output are
byte-identical before and after (the UX-158 caps hold).
