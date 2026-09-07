# UX-768: the closing note is a shell argument, and its backticks run

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** every round that closes a row with a note naming a command | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

The documented closing call in `CLAUDE.md` passes the note as one
shell-quoted argument:

```text
dev_close_task.py UX-NNN --move --note "…" then --check --write
```

The register is backtick-dense — 330 of the closed rows carry a
backticked span in the note — and inside a double-quoted shell word a
backtick is command substitution, not markup. Round 105's own closing
note quoted the command form its hook had walked past:

```text
… so `git status && git push origin master` walked through with exit 0
```

Both halves ran. `git status`'s stdout was substituted into the note
and written to `docs/backlog/scenarios/closed.md:752`, splitting one
row across seventeen lines:

```console
$ sed -n '752,768p' docs/backlog/scenarios/closed.md | head -3
| UX-762 | … at the first git invocation, so On branch claude/build-optimization-audit-hk2xne
Your branch is ahead of 'origin/claude/build-optimization-audit-hk2xne' by 2 commits.
  (use "git push" to publish your local commits)
```

`test_docs_links_and_commands.py::test_every_table_row_has_its_header_cell_count`
caught the garbling at the gate — *"752: 5 cells against a 6-cell
header"* — which is the bounded half.

The unbounded half is that `git push origin master` also ran. It failed
only because no local `master` exists:

```console
$ git branch --list master main
  main
$ git ls-remote --heads origin master
(no output)
```

A note quoting `git push -f origin main`, `rm -rf`, or any branch name
that does exist would have executed it. The session's standing
instruction is never to push to a branch other than its own; a note
*describing* a push is one substitution away from making one, and no
guard reads the note before it becomes argv.

## Required Fix

1. Take the note off the command line. `--note-file <path>` reads the
   note from a file, and the file never transits a shell word. Keep
   `--note` for the one-word case, or drop it.
2. Change the documented invocation in `CLAUDE.md`'s command table and
   in `fixing-guide.md` wherever the closing call is shown, so the next
   round copies the safe form.
3. Guard the residue: a note that arrives already containing a newline
   is a substituted note, not a written one — `_close_one` can refuse
   it by name rather than letting the cell-count guard find it later.

## Out of Scope

- The other flags. `--scenarios`, `--round`, `--date` and `--topic`
  take short literal values that no round writes backticks into — the
  exposure is the prose note, and widening the fix hides which
  argument was the hazard.
- `test_every_table_row_has_its_header_cell_count` — it did its job,
  and it is the reason the damage was one row and not a silent one.
- The `PreToolUse` push gate (`UX-762`, `UX-767`) — a substitution
  inside a tool call it does intercept would still be a Bash call and
  would still be seen; this row is about the note, not the channel.

## Acceptance Test

```console
$ python3 tools/dev_close_task.py UX-NNN --move --note-file /tmp/note.md
$ printf 'a\nb\n' | python3 tools/dev_close_task.py UX-NNN --move --note "$(cat)"
UX-NNN: --note is one line; a multi-line note is a substituted note (UX-768)
```

plus a guard that reddens when `--note` accepts a newline.

## Outcome

(open)
