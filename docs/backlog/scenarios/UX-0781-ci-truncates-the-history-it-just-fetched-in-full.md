# UX-781: CI truncates the history it just fetched in full

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-776 (the refusal whose detector this falsifies) | **Serves:** the round reading a red CI job that the same tree passes locally | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`test (3.11)` was the only red job on `9fba634`, and inside it only
step 27. Step 10 — the **whole suite** — was green eight steps
earlier, on the same runner and the same checkout:

```text
 6 Lint                                    success
10 Test (with a timing report)             success   <- full suite
13 The branch's own diff, ...              success
27 Test (small tier, single process)       FAILURE   <- same tree
```

Step 13 is what changed between them. `ci.yml:158` ran

```console
$ git fetch --no-tags --depth=200 origin main
```

and a depth fetch **creates** a boundary on a complete clone:

```console
$ git clone file:///…/buildstream-graph-analysis fullprobe
$ git -C fullprobe rev-list --count HEAD ; ls fullprobe/.git/shallow
1541
ls: cannot access 'fullprobe/.git/shallow': No such file or directory
$ git -C fullprobe fetch --no-tags --depth=200 origin main
$ git -C fullprobe rev-list --count HEAD ; ls fullprobe/.git/shallow
855
fullprobe/.git/shallow
```

The job asks for `fetch-depth: 0` at checkout and throws it away at
step 13. Every later step reads a cut history — which is why the
register derived rounds 70+ and the ledger's, and reported rounds 7–69
as "written but not derived".

Two guards were in position and neither fired.

`test_ci_asks_for_the_history_these_guards_read` (`UX-637`) asserts
`"fetch-depth: 0" in workflow` — true, and true the whole time. It
reads the checkout, not what the job then does to the clone. The
sentence it means is "CI is the machine that must not have a shallow
clone"; the sentence it checks is "the checkout asks for one".

`is_shallow()` (`UX-776`, closed two commits earlier) reads whether a
boundary's **parent object is absent**. On this truncation every
object is still on disk:

```console
$ python3 -c "…; print(reg.is_shallow('fullprobe'))"
False                       # on a repository git had already cut
```

That is the third proxy in a row for one question. The marker's
existence was the first, object-presence the second, and both were
committed as fixes. The property that matters is neither: a commit in
`.git/shallow` is parentless to *every* traversal whatever objects
exist, so the only question is whether one lies on the walk this
derivation runs.

## Required Fix

1. `ci.yml:158` fetches without `--depth`. The objects are already
   present; only the ref needs updating.
2. `is_shallow()` asks whether `.git/shallow` names a commit that is
   an ancestor of `HEAD` — the traversal, not the object store.
3. `test_ci_asks_for_the_history_these_guards_read` gains a sibling
   that reads **per job**: no job that checked out at `fetch-depth: 0`
   may run a depth fetch. Per job because the two are opposite
   operations on opposite clones — `agent-config` checks out at the
   default depth and the same flag deepens it, so a clause grepping
   the whole file would red on a correct line.
4. The register guard's assertion carries `check()`'s own words. It
   asserts on `check()` and printed everything except its output, so a
   truncated history and a real drift arrived as the same sentence.

## Out of Scope

- Making the register's round set derive from committed material
  rather than `git log`. That is a real question — the documents and
  ledger yield 63 rounds identically in every clone against git's 71 —
  but it is a redesign of what the register *is*, and this row is
  about CI cutting the history the current design reads. Filed
  separately rather than smuggled in here.
- `UX-776`'s round-register row content. The 71 rows it wrote are
  correct for a complete clone and stay.

## Acceptance Test

```console
$ python3 -m pytest tests/unit/test_a_guard_that_reads_history_declares_its_depth.py tests/unit/test_the_round_register_is_derived.py -q
```

Green on this tree; red when `--depth=200` returns to the `test` job's
base-diff step, when `agent-config`'s deepening fetch is dropped (the
clause would then be guarding a distinction that no longer exists),
when `is_shallow()` reverts to either earlier reading, or when the
register guard's message drops `check()`.

## Outcome

### The gap, measured

The failing job's own step list is the whole diagnosis: step 10 ran
the entire suite green, step 13 fetched at `--depth=200`, step 27
re-ran the small tier and the register guard failed. Same runner, same
checkout, three steps apart.

```console
$ git -C fullprobe rev-list --count HEAD     # complete clone
1541
$ git -C fullprobe fetch --no-tags --depth=200 origin main
$ git -C fullprobe rev-list --count HEAD
855
$ python3 -c "…print(reg.is_shallow('fullprobe'))"
False            # UX-776's reading, on a history git had already cut
```

`is_shallow()` read False because no parent object is missing — the
clone was complete before the fetch, so nothing was ever deleted. Git
still refuses to walk past a commit named in `.git/shallow`,
whatever objects exist.

### The close, measured

`ci.yml:158` drops `--depth`; `agent-config`'s fetch at line 648 keeps
it, because that job checks out at the default depth and the same flag
deepens there. `is_shallow()` asks `git merge-base --is-ancestor
<boundary> HEAD` — the traversal, not the object store. The workflow
clause reads jobs rather than the file, and a second clause asserts
that a deepening job still exists, so the distinction cannot quietly
become vacuous. The register guard's assert carries `check()`.

```console
$ python3 -m pytest tests/unit/test_a_guard_that_reads_history_declares_its_depth.py tests/unit/test_the_round_register_is_derived.py -q
32 passed
```

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | `is_shallow()` back to the parent-object reading (`UX-776`'s) | `test_a_depth_fetch_onto_a_complete_clone_is_shallow` |
| M2 | `is_shallow()` back to marker-existence | `test_a_left_behind_marker_is_not_a_shallow_history` |
| M3 | `--depth=200` restored in the `test` job's base-diff step | `test_no_later_step_regrafts_a_boundary_onto_it` |
| M4 | `agent-config`'s deepening fetch dropped | `test_the_clause_above_reads_jobs_and_not_the_whole_file` |

M4 is the one that matters for the population: it proves the clause
is job-scoped rather than a grep, and that it fails when the case it
distinguishes disappears.

The stale-marker guard was strengthened first — it wrote an **empty**
`.git/shallow`, which passes under every reading including the two
falsified ones. It now names a real commit `HEAD` cannot reach, so M2
has something to redden.

### Deviation from the Required Fix

None on the four items. Two decisions taken inside them:

- A shallow clone still **fails** rather than skipping. The precedent
  (`UX-637`, `tests/browser.py`) is a declared skip, and it was
  declined here: with the workflow fixed nothing in CI is cut, a
  developer's cut clone gets a message naming `git fetch --unshallow`,
  and a new census reason would buy silence in exactly the job this
  row was filed on.
- The register's dependence on `git log` reachability is untouched
  and filed as `UX-782`. It is a redesign of what the register is,
  and it carries its own trap (dates read from the document the guard
  compares against), which does not belong in a CI fix.
