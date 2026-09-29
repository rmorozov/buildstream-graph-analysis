# UX-1064: a pseudonym in any text resolves back to the real name

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1061 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 4 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** cli | **Area:** bga | **Shape:** mechanical

**Guard:** test_a_pseudonym_resolves_back.py

## Motivation

The owner asked to understand which internal elements a reader means
"without hand assignment".

## Required Fix

A resolve subcommand in `bga/cli.py` rewrites every pseudonym in stdin
or a file (a reply, a `.bst` patch) back to its original and lists
pseudonym-shaped tokens it cannot map. The viewer takes the map to
render real names locally. A map whose fingerprint differs from the
bundle's is refused.

## Out of Scope

Anything sent off the owner's machine.

## Acceptance Test

`tests/unit/test_a_pseudonym_resolves_back.py`: resolve(anon(text)) ==
text on the golden fixtures' uids; an unknown token is listed; a foreign
map is refused. Mutation: skip the fingerprint check, and the foreign
map resolves to wrong names.

## Outcome

**Gap measured.** `bga/anonymize.py` had `pseudonymize`/`pseudonymize_element_path`
and a `PseudonymMap` (UX-1061) but no reverse path: nothing rewrote a
pseudonym found in arbitrary text, nothing reported an unmapped token,
and nothing refused a map keyed to a different project.

**Close measured.** Added `resolve_text(text, pmap)` (token regex over
`CLASS_PREFIXES`, replaces via `pmap.resolve`, collects unknown tokens
in first-seen order) and `check_fingerprint(key, expected)` /
`FingerprintMismatch` to `bga/anonymize.py`; wired `bga bundle --resolve
--key-fingerprint FP` into `bga/cli.py` (`cmd_bundle` dispatches to
`_bundle_resolve`, a fourth mode of the mutually-exclusive `--export`/
`--load` group rather than a new top-level command, which would have
made the newest release row `extending` and forced cutting `0.5.0`
behind a walk this round does not have), reading stdin, checking the
fingerprint before ever touching the map, printing unknown tokens to
stderr. Manual repro:
`echo "rebase j-xlqb.bst:d-tbec/d-ozlr/e-gap6.bst plus e-abcdef" | bga
bundle --resolve --key-fingerprint <fp>` → `rebase
base.bst:components/gtk/gtk3.bst plus e-abcdef` on stdout, `Unresolved
pseudonym-shaped tokens (1 token): e-abcdef` on stderr; a wrong
`--key-fingerprint` exits 2 with `Error: map key fingerprint … does not
match the bundle's …`. `bga view --resolve` is left out: the viewer
taking the map needs the page, out of this mechanical CLI track's file
(`bga/cli.py`, `bga/anonymize.py`).

**Mutation table.**

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `_bundle_resolve` calls `check_fingerprint` before resolving | drop the `try`/`check_fingerprint` call from `_bundle_resolve` | `test_the_cli_refuses_a_foreign_map_by_fingerprint` | 1 of 4 in the new file |
| `resolve_text` lists an unmapped token | drop the `unknown.append` branch | `test_an_unknown_pseudonym_shaped_token_is_listed_not_dropped` | 1 of 4 in the new file |

**Session decision.** A word shaped like `e-mail` matches the token
regex and is listed as unresolved rather than silently kept; fail-safe.
