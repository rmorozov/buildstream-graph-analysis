# UX-871: a junctioned element finds its kind

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-843 | **Found by:** round 121, the user (a real project under a junction, GNU Make 4.4 on the host) | **Serves:** R2 (an element behind a junction joins the jobserver by its kind) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical

## Motivation

`bst show`'s `%{name}` is the junction-qualified name
(`freedesktop-sdk.bst:components/zlib.bst`, `Plugin._get_full_name`),
so the kinds map is keyed that way; the shim derives the element from
bwrap's `--dir` (`element_from_build_root`), which BuildStream fills
from `%{element-name}`, the project-relative name with no junction
prefix. `_element_kind_env`'s exact lookup misses every junctioned
element, silently, and each reads `unknown_kind` with no warning. No
example in this repository has a junction, so nothing exercised it.

## Required Fix

`tools/bst_native_build_tracer.py`: `_parse_element_kinds` stores
each name under both spellings (the full name and the name after the
last `:`), and the map records the junction prefix it stripped;
`tools/native_trace/bwrap_shim.py`'s lookup stays exact. The capture
counts the junctioned elements it resolved in `jobserver_kinds_read`.

## Decomposition

Input classes: no junction, one level, two levels
(`a.bst:b.bst:c.bst`); the journey it extends is `UX-843`'s join on a
junctioned project.

## Out of Scope

Two junctions shipping elements of the same relative name (a collision
the map records and the first wins; a later row if it happens).

## Acceptance Test

`tests/unit/test_bwrap_shim.py`: `BST_TRACE_ELEMENT_KINDS` written from
a `bst show` line `sdk.bst:foo/bar.bst cmake` resolves `--dir
buildstream/proj/foo/bar.bst` to `cmake`; an unjunctioned name still
resolves; mutation: store the full name only - red.

## Outcome

**Gap measured.** Pre-fix `_parse_element_kinds` stores each line under
its one printed spelling only. On `sdk.bst:foo/bar.bst cmake\nplain.bst
autotools\na.bst:b.bst:deep.bst meson\n`, the pre-fix shape (reproduced
by the "store the full name only" mutation below) leaves `foo/bar.bst`
and `deep.bst` absent from the map, so `element_from_build_root`'s
project-relative name never matches: `_element_kind_env("foo/bar.bst")
-> None` where the fix gives `"cmake"` - the exact silent
`unknown_kind` the Motivation names.

**Close measured.** `_parse_element_kinds` now stores both the full
(junction-qualified) spelling and the name after the last `:`, first
junction wins a collision, and the map carries `.junctions`/
`.collisions` counts. `tests/unit/test_native_build_tracer.py -k
parse_element_kinds`: `6 passed` (3 new: both spellings + `.junctions
== 2`, a collision keeps `cmake` and counts 1, an unjunctioned map
counts 0). `tests/unit/test_bwrap_shim.py -k junctioned`: `1 passed` -
the map written the way the tracer writes it, `_element_kind_env`
(unchanged, exact lookup) resolves `foo/bar.bst`, `plain.bst`,
`deep.bst`. `make test-touching` (104 files, direct `pytest -n 4`,
timeout under load): `2672 passed, 35 skipped in 459.62s`. `ruff
check`: clean. `dev_sizes.py --check`: `tools/bst_native_build_tracer.py`
grew 8614->8644 lines, adopted (`--adopt --force`). `dev_baseline.py
--check`: clean, no new findings.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| store the full name only (drop the short-spelling/junctions/collisions logic) | `test_parse_element_kinds_resolves_both_spellings_of_a_junctioned_name`, `test_parse_element_kinds_a_collision_keeps_the_first_and_counts_it`, `test_a_junctioned_elements_kind_resolves_through_the_real_env_map` | 3 reddened -> reverted, 7/7 green |
| drop the collision count (`elif owner != name: pass`) | `test_parse_element_kinds_a_collision_keeps_the_first_and_counts_it` | 1 reddened -> reverted, 6/6 green |
