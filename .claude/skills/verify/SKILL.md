---
name: verify
description: Close a backlog task in this repository - which tier to run, which suite, which two copies of the status marker, and what the Outcome section has to contain. Use when finishing a UX-* task, before committing.
---

# verify

The Definition of Done as a sequence you can run. The rule lives in
[`docs/contributing/fixing-guide.md`](../../../docs/contributing/fixing-guide.md)
§3 — this is the entry point, not a second copy. When the two disagree,
the guide is right and this file is a bug.

## 1. The acceptance test, exactly as the task file wrote it

Run the command in the task's **Acceptance Test** section verbatim and
paste the real output into the file. Not a paraphrase and not a
description of what it printed.

## 2. The tier your change touched

```bash
make test-small      # 21s  - the default tier; most edits need only this
make test-medium     # ~3m  - spawns a process or a node harness
make test-large      # ~2.5m - scale fixtures, real process trees
make test-fast       # small + medium: everything needing no real bst
```

Tiers come from measured per-file duration in
[`tests/tiers.py`](../../../tests/tiers.py). Use them for the edit-run
loop and for re-running one guard after a mutation. They are not a
substitute for step 3.

To run one file or one guard while iterating:

```bash
python3 -m pytest tests/unit/test_<file>.py -q
python3 -m pytest tests/unit/test_<file>.py -q -k <substring>
```

## 3. The whole suite, and lint

```bash
make test    # ~5m10s
make lint    # ruff + PyMarkdown; both must be clean
```

`make test` before you mark anything done. A tier run is not evidence
about the suite.

## 4. The two copies of the status marker

The row in `docs/backlog/scenarios/README.md` and the `**Status:**`
line in the task file are two hand-maintained copies of one fact and
have drifted in three separate rounds. Change both in the same commit,
and move the row to
[`closed.md`](../../../docs/backlog/scenarios/closed.md) when it closes
— open rows live in `README.md`, closed ones verbatim in `closed.md`.
The index counts at the top of `README.md` (`N open`, and the per-topic
table) change too.

`tests/unit/test_docs_links_and_commands.py::test_the_table_status_matches_the_task_files`
fails naming the item if you miss one.

## 5. The Outcome section

Append to the task file. What it must contain, because a later round
will read it instead of the code:

- the measurement that shows the gap existed, pasted;
- the measurement that shows it is closed, pasted;
- **every mutation you applied to falsify a new guard**, and that it
  went red (see the `falsify` skill);
- any guard of your own that turned out not to discriminate, and why —
  this repository has found five, and each one was worth more written
  down than quietly fixed;
- **Deviation from the Required Fix**, explicitly, even when it is
  "none";
- the tier and full-suite lines with their real numbers.

## 6. Before the commit

- Did the change make a document wrong? Fix it in the same commit
  (fixing guide §3.10).
- Does it need documentation you are **not** writing now? File a row
  before the commit lands (§3.11) — id, one line, 🔴, topic `docs`.
- Did a number an earlier task file presents as current move? Annotate
  that file (§3.6); `git grep <old figure> docs/backlog/scenarios`.
