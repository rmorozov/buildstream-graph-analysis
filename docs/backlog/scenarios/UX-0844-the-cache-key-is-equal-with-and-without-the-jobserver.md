# UX-844: the cache key is equal with and without the jobserver

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-843 | **Found by:** round 117, Direction 20 | **Serves:** R4 (artifacts built either way are shared) | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

BuildStream folds the composed environment minus `environment-nocache`
into the key (`element.py:2319-2339`, 2.8.0); the shim's injection is
spliced into `bwrap`'s argv after composition and never passes through
it; the shipped plugins nocache `JOBS` and `MAKEFLAGS` besides. So the
key is safe by construction - and no measurement in the tree says so:
`UX-679` compared `%{env}`, never `%{full-key}`, and a custom plugin
that keys its `JOBS` would split the cache silently between the two
modes.

## Required Fix

A guard in CI's examples job (`.github/workflows`, the `bst-examples`
job): `bst show --format '%{name} %{full-key}'` over examples/06 with
the mode off and on, diffed - equal; then a build under the mode
followed by `bst build` without it reports every element cached (the
pasted `bst build` summary). The tracer's report records the key set's
hash so a later capture can be compared. `docs/guides/cli.md` states
the rule in one sentence beside `--jobserver`.

## Out of Scope

A key-safe custom plugin - the project's own `environment-nocache`
is the fix, named in the guide.

## Acceptance Test

`tests/unit/test_the_key_is_equal_either_way.py` runs the two `bst
show` commands on the fixture project (skips without `bst`); mutation:
a fixture plugin that keys `JOBS` - red, naming the element.

## Outcome

**Gap measured.** Nothing in the tree ran `%{full-key}` under the
mode: `UX-679` compared `%{env}`, never the key. Confirmed empirically
against `tests/fixtures/bst_show_project` before this track wrote a
guard - `bst show --format '%{name} %{full-key}'` twice, clean vs. a
host carrying `MAKEFLAGS`/`JOBS`/`CARGO_BUILD_JOBS` and all 19
`BST_TRACE_*` names - equal, and no name reached `%{env}` either. The
real gap: a *custom* plugin can still key a host value through its own
`get_unique_key()`, a channel `environment-nocache` cannot reach at
all - demonstrated below, not asserted.

**Close measured**, `python3 -m pytest tests/unit/test_the_key_is_equal_either_way.py tests/unit/test_the_cache_key_set_is_a_hash_of_bst_show.py -q`:

```text
tests/unit/test_the_key_is_equal_either_way.py ..                        [ 28%]
tests/unit/test_the_cache_key_set_is_a_hash_of_bst_show.py .....         [100%]
============================== 7 passed in 2.99s ===============================
```

Live, `examples/06`'s `all.bst` (11 elements, real toolchain staged):
`%{full-key}` equal clean vs. leaking, byte for byte. A real build
under `--jobserver 4` (`cache_key_set`: `{"sha256":
"713ad68...", "elements": 11}`), then a plain `bst build all.bst` with
no cache clear: `Pipeline Summary Total: 11`, all 11 lines `cached`.

**Mutations verified red and reverted (3):**

| mutation | reddened | revert |
|---|---|---|
| a throwaway fixture plugin (`get_unique_key` returns `{"jobs": os.environ.get("JOBS")}`) on a temporary `mutant.bst`, project.conf's `plugins:` edited to load it | `%{full-key}` for `mutant.bst` differs clean vs. `JOBS=-j4` (`a6c02877...` vs `3bcda0b1...`) - the guard's own message-building logic, run against it, names `mutant.bst` | `git checkout -- project.conf`; plugin dir and `mutant.bst` deleted (untracked) - guard green again on the real fixture |
| `hash_cache_key_lines`: sort dropped | `test_many_lines_are_order_independent` | reverted from a pre-edit backup; 5/5 green |
| `hash_cache_key_lines`: hash over names only | `test_a_different_key_for_the_same_name_changes_the_hash` | same revert; 5/5 green |

Deviation: the CI step targets `bst_command_targets(cmd)` - a `.bst`-
suffix filter over the wrapped command's argv, not a project-wide
default - because `bst show` with no target needs one named. The
guard's docstring first cited `bwrap_shim.py` by name and
`dev_touching`'s grep picked it up as a false edge, pushing
`tools/native_trace/bwrap_shim.py` over `HANDFUL` in
`test_the_loop_stays_fast.py`; reworded to name the mechanism, not the
file. `dev_touching.py --spread --write` moved the fixing guide's
figure (541→543 test files, both new files stayed under the map's own
25-file entries). CI's `bst`-tier pin moved 47→49 (two new
`@pytest.mark.bst` tests) - `UX-851` also moves this pin and the merge
reconciles. One new `S603` baseline entry (`tools/bst_native_build_tracer.py`,
the pre-build `bst show`), authorised `UX-844`, matching `UX-841`'s
precedent (`shutil.which` first avoids `S607`).
