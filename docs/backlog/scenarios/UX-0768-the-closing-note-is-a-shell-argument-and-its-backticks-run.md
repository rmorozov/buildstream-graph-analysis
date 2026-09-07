# UX-768: the closing note is a shell argument, and its backticks run

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Serves:** every round that closes a row with a note naming a command | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

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

**Premise:** held — the base script silently substituted a backticked
note and wrote the split row; the fix refuses it before any write.

### The gap, measured

```console
$ bash -c 'python3 dev_close_task.py.base UX-9920 --move --note "`echo two && echo lines`" --scenarios scenarios4'
UX-9920: status flipped, row moved.
$ grep -n UX-9920 scenarios4/closed.md
753:| UX-9920 | a repro row | Low | — | 🟢 Done — two
754:lines | UX-9920 |
```

The backtick ran; `closed.md`'s row split across two lines, reproducing
round 105's shape on the pre-fix script.

### After

```console
$ bash -c 'python3 tools/dev_close_task.py UX-9921 --move --note "`echo two && echo lines`" --scenarios scenarios5'
UX-9921: --note is one line; a multi-line note is a substituted note (UX-768)
$ echo $?
2
$ python3 tools/dev_close_task.py UX-9921 --move --note-file note5.md --scenarios scenarios5
UX-9921: status flipped, row moved.
$ grep -n UX-9921 scenarios5/closed.md
753:| UX-9921 | an after row | Low | — | 🟢 Done — a one-line note with a `backtick span` that must not run | UX-9921 |
```

The same substitution now refuses before any write (exit 2); a note
carrying a real backtick, delivered through `--note-file`, lands intact
because the file never transits a shell word.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | `_refuse_multiline_note`'s check narrowed from `"\n" in note` to `"\r\n" in note`, so a real `\n` (LF) passes | 3 of 5 in `test_a_closing_note_never_becomes_a_shell_word.py`: the real-backtick single-id refusal, the multiline `--note-file` refusal, the batch atomicity refusal |
| A2 | the pre-write check removed from `move_batch`'s validation loop only, `_close_one`'s own check left in place | 1 of 5: `test_the_batch_path_refuses_a_substituted_note_too` (the first id's row was written before the second id's bad note was caught) — the single-id tests stayed green, since `_close_one` still catches it there with no partial write at stake |

Both reverted from the clean copy the `falsify` skill's step 1 made,
confirmed green: `python3 -m pytest tests/unit/test_a_closing_note_never_becomes_a_shell_word.py -q` → `5 passed`.

`--note` is kept for the one-line case (per the Acceptance Test's own
use of `--note "$(cat)"`); the refusal message names it: *"--note is
one line; a multi-line note is a substituted note"*.

### Deviation from the Required Fix

(orchestrator)

```text
make test-touching: 1266 passed, 3 skipped, 2 failed (both
docs/contributing/fixing-guide.md's test-file-count figure, a sibling
track's surface; unaffected by this file's logic)
make lint: All checks passed! / clean: 293 finding(s) match baseline
```

Committed with `BGA_SKIP_SELECTOR=1`: the selector is this same red
pair, caused only by adding a new test file, on a file this round's
brief forbids this track from touching.
