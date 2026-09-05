# UX-191: tab completion without a rewrite

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-158 (the help surface completion complements), UX-126 (the alias grammar worth completing) | **Topic:** cli | **Area:** bga

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

---

## What was built

**The decision, first, because it was the question the feedback
asked.** `click` was considered and declined. `argcomplete` completes
an argparse program as it stands: a `PYTHON_ARGCOMPLETE_OK` marker in
the first kilobyte of the entry point, one
`argcomplete.autocomplete(parser)` call, an optional extra. A click
migration would touch all fifteen subcommands, re-render `UX-158`'s
help from scratch (click formats its own), and buy nothing argcomplete
does not already give. Recorded here rather than in a commit message,
and revisitable if argcomplete ever cannot complete something users
need.

**The integration is two lines.** `# PYTHON_ARGCOMPLETE_OK` at
`bga/cli.py:2`, and `_maybe_complete()` at the top of `main()` -
before the schema hook and before the alias dispatch, so a TAB never
pays for a tool import. It is inert without the shell hook:
`argcomplete.autocomplete` returns immediately unless `_ARGCOMPLETE`
is in the environment, and a missing `argcomplete` is a caught
`ImportError`.

**Three completers carry the value:**

1. `_snapshot_completer` - `@last`, `@prev`, and the store's own
   stamps, which is the completion the feedback named (*"bga
   cache-trend"*, whose argument is a run). Attached by
   `_attach_run_completers`, which walks every subparser driven off
   `_RUN_DIRECTORY_ARGS`/`_RUN_DIRECTORY_LIST_ARGS`/`_PLANE2_ARGS` -
   the same three lists `_resolve_run_aliases` uses, so an argument
   that learns to take an alias gets completion for it without a
   second edit. 22 arguments are completable.
2. `_command_completer` - subcommands **and** all seventeen `UX-67`
   aliases (the Motivation's "fifteen subcommands" and this item's
   original "ten aliases" were both estimates; the real counts are 11
   and 17, and a guard now reads them from `TOOL_ALIASES` rather than
   from a list a human keeps in step).
   The aliases are not argparse subparsers by design (registering them
   would import every tool to build the parser, on every `bga
   analyze`), so completion reads `TOOL_ALIASES` directly. A completion
   that offered half the tool would be worse than none.
3. `_element_completer` - element names for `bga blast`, from the
   project's own files.

Every one is best-effort by construction: a completer that raises
reaches the user's shell as a traceback in the middle of a command
line, so anything unreadable answers nothing.

Packaging: `completion = ["argcomplete>=3.0"]` extra, plus `dev`.
Documented in README (3 lines) and in `docs/guides/cli.md`.

Tests: 17 new (`tests/unit/test_tab_completion.py`), driven through
the real `argcomplete` entry point where the answer does not depend on
a project on disk, and through the completer functions where it does.
Seven mutations, each red.

**A defect the guards found in the fix itself.** `_snapshot_completer`
called `os.path.basename` - and `bga/cli.py` does not import `os`. The
`NameError` was swallowed by the deliberate broad `except`, so the
completion did not crash; it silently answered nothing, which is
exactly the dead TAB with no explanation the completer's own docstring
warns about. `Path(snapshot).name` instead.

**A guard that guarded nothing, found by falsifying it.**
`test_no_project_means_no_answer` asserted the element completer
returns `[]` outside a project. Deleting the `project is None` branch -
so the completer walked the current directory instead - left it green,
because a `tmp_path` holds no `.bst` files either way. But the
directory a user TABs in outside a project is `$HOME` or `/`, and a
recursive walk of that on every keypress is the failure the design
avoids. Rewritten to pin the *call*, not the answer: `discover_element_names`
must not be invoked at all. It reddens now.

**Deviation from the Required Fix:** `bga doctor` says nothing about
completion. The item allowed either way ("only if trivially checkable,
else nothing"); whether a shell rc has been sourced is not checkable
from inside the process, so nothing.

