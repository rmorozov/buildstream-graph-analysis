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

## 2. The tests that touch what you changed

```bash
make test-touching   # the files that name the modules your diff touched
```

Measured on a one-module diff: **4s**, 7 files, 123 tests (`UX-336`).
A *selector*, not a gate - a grep-derived set can miss a test that
exercises a module without naming it, which is why step 3 is unchanged.
`make test-touching ARGS=--why` says what selected each file.

Then the tier, when the change is wider than one module:

```bash
make test-small      # 11s  - the default tier; most edits need only this
make test-medium     # ~1m50s - spawns a process or a node harness
make test-large      # ~1m15s - scale fixtures, real process trees
make test-fast       # small + medium: everything needing no real bst (~2m)
```

Every target runs `-n auto` (`UX-336`). `PYTEST_XDIST= make test-small`
turns it off for a single-process run - which is what you want with
`-x`, or under `pdb`.

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
make test    # ~3m15s at -n auto (10m40s single-process)
make lint    # ruff + PyMarkdown; both must be clean
```

And when your change moved what a file does rather than only what it
asserts:

```bash
make test-tiers   # the same run, plus which files outgrew their tier
```

`UX-418`: the suite with a junit report, then
[`tools/dev_tier_drift.py`](../../../tools/dev_tier_drift.py) against
the floors in `tests/tiers.py`. It costs a parse, not a second suite.
**Here and not in CI** — the floors are seconds measured on this kind of
machine, and CI's runner differs from it per file rather than by a
factor, which three CI runs established the hard way. CI runs its own
half (`UX-420`): the same tool with `--against`, reading
`tests/ci_reference.json`, which is one CI run's own totals. When that
step says a file drifted and you cannot reproduce it here, that is the
point — it is CI's clock, and the answer is `--record` from a green run
rather than a number changed until it is quiet.

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
fails naming the item if you miss one, and

```bash
python tools/dev_close_task.py UX-NNN --move --note "one line for closed.md"
python tools/dev_close_task.py --check
```

does the four mechanical edits and reports what disagrees (`UX-336`).
`--move` refuses when the task file has no Outcome section.

## 5. The Outcome section

```bash
python tools/dev_close_task.py UX-NNN --outcome --round NN --date YYYY-MM-DD
```

prints the skeleton with the headings below and every measurement left
blank - `UX-336`, and blank on purpose: a helper that pre-filled them
would be inviting the unmeasured claim this list exists to prevent.

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
