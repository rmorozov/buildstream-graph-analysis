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
make test    # 3m45s-8m52s at -n auto across rounds 74-81 on the same
             # 4 cores - the spread is the machine (UX-551); the
             # fixing guide carries every reading
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
`UX-455`: plus a re-run of each file it is about to name, **alone and
single-process**, because the report is `-n auto` and the floors are
not - so the seconds it prints are already the ones to put in
`tiers.py`, and a file the parallel run accused and the confirmation
cleared is printed as that rather than as drift. `--no-confirm` reads
the parallel report on its own.
**Here and not in CI** — the floors are seconds measured on this kind of
machine, and CI's runner differs from it per file rather than by a
factor, which three CI runs established the hard way. CI runs its own
half (`UX-420`): the same tool with `--against`, reading
`tests/ci_reference.json`, which is one CI run's own totals. When that
step says a file drifted and you cannot reproduce it here, that is the
point — it is CI's clock, and the answer is `--record` from a green run
rather than a number changed until it is quiet.

`UX-442`: that step reports a file only when **two consecutive runs**
of the branch agree it is over both gates, carried between runs in a
cache. So a branch's first run cannot report drift, and a real
regression is named one run after it lands. That is the price of the
three round-69 reds that no diff could have caused; the run that sees
an excursion once still prints it, marked as unconfirmed.

`make test` before you mark anything done. A tier run is not evidence
about the suite.

### When CI's drift step is red and the file really did get slower

`UX-447`: the route, because `--record` on your own machine writes
**your** seconds and `UX-418` established those cannot be compared to
CI's in any form. The numbers to commit exist only in CI's own run:

1. Open the red `test (3.11)` job's summary on that run.
2. Download its **`ci-reference-candidate`** artifact - one file,
   `ci_reference.candidate.json`, written by the same tool with
   `--record` and kept for 30 days. It is the whole document, not a
   diff. `UX-457`: if you cannot reach GitHub's artifact host - an
   agent session behind an egress policy gets `403 CONNECT tunnel
   failed` from it and from the run-log host both - read the
   **`tier-reference`** job's log on the same run instead. That job
   downloads this artifact and `cat`s it, and does nothing else, so
   its log *is* the document.
3. Replace `tests/ci_reference.json` with it.
4. Commit it in the same commit as the change that made the file
   slower, with a line in the task file's Outcome saying which run it
   came from and why the file now costs what it does.

Appending one row by hand is the other shape, and it is the one this
repository has used more often - the gate prints `N.Ns` for the file it
is complaining about, and that figure **divided by the run's printed
shift** is the number to put in `files`. Divided, because
`expected = known x shift` is the arithmetic the gate does: a raw
append bakes that run's slowness into the row as permanent slack.
`tests/ci_reference.json`'s own `note` carries every append made that
way, with the run id and the shift each was taken from.

Do not run `--record` locally and commit the result. It is not the same
document: it is 380 files of this machine's clock replacing 380 files
of CI's, and the gate will be quiet for the wrong reason.

**After adding a test file, do nothing.** `UX-503`: a file the
reference does not carry is printed as *recorded*, not failed on, and
the default branch's own run adopts the row after the merge.

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
python tools/dev_close_task.py --check --write
```

does the mechanical edits and reports what disagrees (`UX-336`).
`--move` refuses when the task file has no Outcome section.

`UX-501`: `--move` touches only the rows. The counts sentence and the
topic table above them are *derived* - `--check --write` regenerates
them from the rows, which is also how two merged tracks get one right
answer instead of a conflict on a line neither of them meant to touch.

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

## 7. When the gate is not on this machine

Some claims cannot be checked here at all. Three of round 68's five
items were about measuring *across* machines, and a session container
has one machine and one clock:

- `UX-421` — "fails on the fastest runner seen and on the slowest"
  needs more than one runner to mean anything.
- `UX-422` — the failure was a loaded runner, and eight CPU spinners
  on four cores did not reproduce it. The floor probe read 0.00 ms
  every time.
- `UX-423` — the reference is CI's own clock, and `UX-418` established
  that a local report cannot be read against it in any form.

For those, CI is not a slower copy of `make test`. It is the only
instrument that exists.

**CI runs on `pull_request` and on pushes to `main`, and nothing
else** — see `.github/workflows/ci.yml`, and
`test_the_workflow_runs_only_where_the_skill_says` holds these two
copies of that fact together. A branch with no PR collects no runs at
all, however many times you push. So when the round's work is of that
kind, open the PR — a draft is fine — *before* the work rather than
after, and let each commit collect a run while you move on.

What follows from that:

1. **Per item:** implement, `make test-touching`, mutate every new
   guard until it reddens, commit, push. Do not wait for the run.
2. **Between items:** read the check runs — one call, and no log
   unless something is red.
3. **At the end:** `make test` here, plus whatever CI has batched up.

**Batch what is cheap to fix late; never batch a design decision.**
Lint, a docs link, an index count, an unrelated module you broke — all
cheap, and CI finds them while you work on the next thing. A wrong
*design* is not: round 66 spent three red CI rounds on three wrong
designs for one check, and four items built on top of one of those
would have meant unwinding four commits.

### Why this is here and not in the fixing guide's hard rules

**One round is not a baseline.** The sequence above is one session's
experience, and nobody has measured whether it costs less than the
alternative — no wall-clock or context figures were collected, so
"it was faster" is not a claim this repository is entitled to make yet.
`UX-420` sized a threshold on one sample and its first armed run named
thirty-one files on an unchanged suite; asserting a process rule on one
round is the same shape of mistake one level up. The trigger fact is a
fact and is stated as one; the loop is guidance until some round
measures it.
