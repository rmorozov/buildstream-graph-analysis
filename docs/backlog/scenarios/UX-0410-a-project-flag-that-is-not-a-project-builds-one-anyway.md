# UX-410: a `--project` that is not a project builds one anyway

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-324 (the refuse-before-writing precedent) | **Serves:** R1, on a mistyped path | **Topic:** capture | **Area:** tools

## Motivation

Found through the round-64 walker's own mistyped relative path: with
cwd already inside example 06,

```text
$ bga snapshot --project examples/06-macro-micro-optimization -- bst build all.bst
```

pointed `--project` at a directory that exists (the phantom
`examples/06-.../examples/06-...` does not — but path resolution
made one) — snapshot created `.bga` under the phantom directory, ran
`bst` with that cwd, and **bst walked up to the real project.conf
and built the parent project**. Green snapshot, store in a directory
the user never meant, measuring a build of a project the flag never
named. `bga doctor` checks for `project.conf`; `bga snapshot` does
not.

## Required Fix

`snapshot` (and `capture`) verify `--project` contains a
`project.conf` before writing anything — the `UX-324` rule applied
to the flag: refuse with the sentence naming the path checked and
the nearest ancestor that *does* hold a `project.conf`, and create
no directory on the refusal path.

## Out of Scope

- Following bst's walk-up semantics on purpose — if someone wants
  the enclosing project they can name it; silently measuring a
  different project than the flag names is the defect.
- The relative-path Plane 2 forfeiture — same walk, different
  mechanism: that is `UX-405`.

## Acceptance Test

- The invocation above refuses, names the checked path, and leaves
  no `.bga` behind (byte-for-byte directory listing, `UX-324`'s
  clause).
- Falsification: skip the check — the refuse-and-write-nothing
  guard goes RED.

## Outcome (round 65, 2026-08-29) — 🟢 Done

### The gap, and the refusal, on the walker's own invocation

Reproduced from inside example 06, where the relative path resolves to
a phantom `examples/06-.../examples/06-...`:

```text
bga snapshot --project examples/06-macro-micro-optimization -- bst build all.bst

before   a green snapshot of the *parent* project, `.bga` under a
         directory the user never named

after    Error: examples/06-macro-micro-optimization does not exist.
         Nothing was captured and nothing was written.
           The nearest project above it is
           /home/user/.../examples/06-macro-micro-optimization. bst
           would have walked up to it and built *that* - which is why
           this refuses rather than proceeding.
         exit 2

         find . -maxdepth 3 -name .bga   identical before and after
```

And the other mistake, a real directory of the wrong kind:

```text
bga snapshot --project /tmp/notaproject -- bst build all.bst
  Error: /tmp/notaproject is not a BuildStream project - it has no
  project.conf. Nothing was captured and nothing was written.
    No enclosing project either. Check the path, or run `bga doctor`
    from inside the project you meant.
  exit 2
```

**Two mistakes, told apart**, which the Required Fix did not ask for
and the walker's own case needs: "it has no project.conf" would have
sent them looking for a file in a directory that does not exist.

The refusal sits beside `UX-324`'s, in `main`, before the sticky
config, the snapshot directory and the store's `.gitignore` — the three
writes on the way past it.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| A1 | the check is never called from `main` | the wrote-nothing clause (1 failed, 5 passed) |
| A2 | the two mistakes get one sentence | the does-not-exist clause (1 failed, 5 passed) |
| A3 | the enclosing project is not named | the names-what-bst-would-build clause (1 failed, 5 passed) |
| A4 | the refusal prints and proceeds anyway | the exit-2 and wrote-nothing clauses (1 failed, 5 passed) |

**Two mutations did not discriminate on their first run, and both are
recorded rather than quietly fixed.**

`A3` was green: the clause asserted `str(tmp_path) in said`, and the
refused path is *inside* `tmp_path`, so the parent's path was already a
substring of the first line. A prefix made the clause trivially true.
It now asserts the sentence — `"nearest project above it is <path>"` —
and A3 reddens.

The fourth mutation of the first sweep removed the `if args.project:`
condition around the check, and **changed no behaviour at all**:
`run_store.project_root` finds a root *by* looking for `project.conf`,
so a resolved root always has one and the condition could never matter.
The condition was deleted rather than the mutation counted — a guard
cannot discriminate a distinction the code does not make — and the
clause that used to sit behind it now holds the equivalence instead: if
the resolver ever returns something else, the documented
run-from-a-subdirectory invocation would start refusing itself.

### Deviation from the Required Fix

**One addition, no subtraction.** The Required Fix asks for one
sentence naming the checked path and the nearest ancestor; this ships
two, because the case that produced the filing is a path that does not
exist and the other is a directory that does. Both name the ancestor.

### Verification

```text
pytest tests/unit/test_a_project_flag_names_a_project.py       6 passed
pytest -k "snapshot or store or capture or doctor"  588 passed, 1 skipped
make lint                                                      clean
```
