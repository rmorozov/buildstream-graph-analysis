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
