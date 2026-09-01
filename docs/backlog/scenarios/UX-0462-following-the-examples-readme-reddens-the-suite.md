# UX-462: following `examples/README.md` reddens the suite

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 72, generating the bulk tree the way `examples/README.md` says to | **Serves:** the contributor who follows the examples guide and then cannot tell their own diff from the guide's side effect | **Topic:** guards

## Motivation

`examples/README.md` tells the reader to run the generator before
building example 09:

> Generate the bulk tree once (it is gitignored, like the toolchain):
> `examples/09-fine-grained-siblings/generate_bulk.py`

Do that, and `make test` goes red:

```text
$ examples/09-fine-grained-siblings/generate_bulk.py
Generated 60000 files under .../examples/09-fine-grained-siblings/files/bulk

$ make test
FAILED tests/unit/test_a_guard_reads_only_what_a_clone_has.py::
       TestEveryPathAGuardNamesIsInTheClone::
       test_no_test_rests_only_on_an_untracked_path
  tests/unit/test_fine_grained_fixture.py ->
      ['examples/09-fine-grained-siblings/files/bulk']
      (and no committed fixture beside it)
1 failed, 5505 passed, 28 skipped in 510.94s
```

Move the generated tree aside and the same guard is green:

```text
$ mv examples/09-fine-grained-siblings/files/bulk /tmp/bulk
$ python3 -m pytest tests/unit/test_a_guard_reads_only_what_a_clone_has.py \
      -q -k untracked_path
1 passed, 9 deselected in 0.94s
```

So the red depends on machine state and on nothing in the diff, which
is the failure mode most likely to be waved off as noise.

The flagged citation is not a path the test reads. It is the whole of
`tests/unit/test_fine_grained_fixture.py`'s mention of it:

```python
assert "examples/09-fine-grained-siblings/files/bulk/" in ignored
```

— an assertion that the string is a **line of `.gitignore`**. The file
never opens it; `UX-276`'s guard cannot tell a path used as a path from
a path compared as text, so it reports the correct rule against the
wrong file.

`UX-276` is right about the class it names and has already been
sharpened twice for the opposite error — `_joined_paths` for fragments
it could not see, `_guards_absence` for a safe shape it did not
recognise. This is the third: a citation that is not a read at all.

## Required Fix

`_cited_paths` drops a literal whose every occurrence in the module's
AST is an operand of a comparison. Compared, never opened — so no
filesystem access can depend on it, and its presence or absence cannot
change the outcome.

Not a spelling rule: a trailing slash, or the word `gitignore` on the
line, would be a proxy for "this is not a read" and fixing guide §5 is
about exactly that. The question the guard asks is whether the file
could open the path, and comparison operands are the one position in
which it provably cannot.

## Out of Scope

- The other two shapes `UX-276` already handles.
- Committing the bulk tree. The root `.gitignore` excludes it on
  purpose — 60,000 inodes whose only purpose is to make staging
  measurable — and `UX-189` settled that a clone does not ship
  generated data.
- `_guards_absence`'s own proxy — its docstring already declares that
  it cannot tell which clauses a skip-mark covers, and names the
  suite-run-with-untracked-paths-moved-aside as the check it only
  approximates. That is a stated limit, not an unnoticed one.

## Acceptance Test

With the bulk tree generated, as `examples/README.md` instructs:

```bash
examples/09-fine-grained-siblings/generate_bulk.py
python3 -m pytest tests/unit/test_a_guard_reads_only_what_a_clone_has.py -q
```

green, and the mutations in the Outcome section red.

## Outcome

**Round 72 · 2026-09-01 · Status: 🟢 Done**

### The gap, measured

Full suite on a quiet box (`load average: 0.11`), with the bulk tree
generated as `examples/README.md` instructs:

```text
FAILED tests/unit/test_a_guard_reads_only_what_a_clone_has.py::
       TestEveryPathAGuardNamesIsInTheClone::
       test_no_test_rests_only_on_an_untracked_path
E   tests/unit/test_fine_grained_fixture.py ->
E       ['examples/09-fine-grained-siblings/files/bulk']
E       (and no committed fixture beside it)
1 failed, 5505 passed, 28 skipped, 1 warning in 510.94s (0:08:30)
```

The whole of the flagged file's mention of that path, which is one
line and is not a read:

```text
$ grep -n "files/bulk" tests/unit/test_fine_grained_fixture.py
65:    assert "examples/09-fine-grained-siblings/files/bulk/" in ignored
```

And the same guard with the generated tree moved aside — the state a
clone and CI are in, and the reason nothing had ever noticed:

```text
$ mv examples/09-fine-grained-siblings/files/bulk /tmp/bulk
$ python3 -m pytest tests/unit/test_a_guard_reads_only_what_a_clone_has.py \
      -q -k untracked_path
1 passed, 9 deselected in 0.94s
```

### The gap, closed

`_compared_not_opened` drops a literal whose every AST occurrence is a
comparison operand; `_cited_paths` subtracts it. With the bulk tree
present:

```text
$ python3 -m pytest tests/unit/test_a_guard_reads_only_what_a_clone_has.py -q
14 passed in 3.47s
```

Four clauses added: the miniature of the filed case, the file that
compares on one line and opens on another, two literals of which only
the compared one is dropped, and the real file against the real tree
(which **skips with the reason** where the tree is absent, per
`UX-213`'s rule that "we could not look" must not read as "we looked
and it was fine").

### Mutations applied

| # | Mutation | Went red |
|---|---|---|
| M1 | `all(...)` → `any(...)` over a literal's occurrences | `test_a_path_compared_on_one_line_and_opened_on_another_still_counts` |
| M2 | the `- _compared_not_opened(text)` subtraction removed | the real check, plus 3 of the 4 new clauses |
| M3 | `(node.left, *node.comparators)` → `node.comparators` | the real check, plus 3 of the 4 new clauses |
| M4 | filter keyed on the file rather than on the literal | `test_the_filter_does_not_swallow_a_different_path`, plus 2 |

M1 and M4 are the two that matter: each isolates one half of the rule
and only its own clause fell over, so neither half rests on the other.

### A guard of my own that did not discriminate

None new. But the round that filed this one had already filed
`UX-461` — "example 09 cannot be built by anyone" — on the strength of
`ls examples/*.sh` finding no staging script. `generate_bulk.py` was
committed all along and `examples/README.md` names it. That row was
withdrawn, and running the generator to prove it is what produced the
red this item fixes.

### Deviation from the Required Fix

None.

### Tier and suite

`tests/tiers.py` comment re-measured 2.1s → 3.5s; same tier (MEDIUM,
floor 1.0s, `LARGE_FLOOR_S` 15.0s), so no list moves and
`tests/ci_reference.json` needs no re-record.

```text
$ make test
5510 passed, 28 skipped, 1 warning in 298.87s (0:04:58)
```

### Two other gates this item's own diff reddened

Both correct, and worth writing down because both are the suite
catching this round rather than this round catching the suite:

- `test_every_out_of_scope_entry_names_a_task_or_states_a_decline`
  (`UX-232`) on the third Out of Scope bullet, which was a bare noun
  phrase. Rewritten to state its reason.
- `test_every_declared_skip_reason_is_known` (`UX-449`) on the new
  `pytest.skip` above, before any machine lacking the bulk tree had
  run the suite. Declared in `tests/conftest.py`.
