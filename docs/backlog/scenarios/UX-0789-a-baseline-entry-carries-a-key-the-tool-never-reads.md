# UX-789: a baseline entry carries a key the tool never reads

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-694 (the baseline), UX-712, UX-703 | **Found by:** round 109, retro-verifying round 102 | **Serves:** the `--check` output that promises to name every forced batch forever | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`tests/quality_baseline.json`'s entries for `tools/dev_sizes.py` and
`tools/dev_mutation.py` (both ruff S603) carry a top-level
`"forced_by": "UX-712"` / `"UX-703"`; `dev_baseline.py`'s
`load_forced` reads `"forced"` only:

```console
$ python3 tools/dev_baseline.py --check
clean: 295 finding(s) match ...; 1 still forced by UX-744; 2 still forced by UX-762; 1 still forced by UX-781
```

No "still forced by UX-712", no UX-703. `UX-712`'s Outcome says the
entry is S602 and was written with `--force --reason`; it is S603 and
was hand-written. The docstring's promise — every forced batch stays
named in `--check` — holds for entries the tool wrote and not for
these two.

## Required Fix

Re-force both entries through `tools/dev_baseline.py --write --force
--reason UX-NNN`, drop the dead key, and have `--check` refuse an
entry with an unknown top-level key so a third hand-written one
cannot land.

## Out of Scope

- The S603 findings themselves — a dev tool's `subprocess.run` with a
  list argument is the accepted shape.

## Acceptance Test

`tests/unit/test_the_baseline_only_shrinks.py` (or the file that
holds `--check`'s clauses) gains: an entry with `"forced_by"` → exit
2 naming the key. Mutation: accept any key — red.

## Outcome

### The gap, measured

Against the original committed baseline (`tests/quality_baseline.json`
at `c13297cf`), `--check` never named either batch:

```console
$ python3 tools/dev_baseline.py --check --baseline <that copy>
clean: 568 finding(s) match ...; 281 still forced by UX-697; 1 still
forced by UX-744; 2 still forced by UX-762; 1 still forced by UX-781
```

`grep -c "UX-712\|UX-703"` on that output: `0`. Both top-level
`"forced_by"` keys had already been dropped by a later `--write`
(`write_baseline` never emits an unknown document key), so the file
itself no longer carried the dead key - only the two untracked
findings remained.

### The close, measured

Removed the two S603 entries by hand, committed that removal (so
`git show HEAD:` stopped carrying them), then re-added them the only
way `--force` can sign a finding - against a HEAD that lacks it:

```console
$ python3 tools/dev_baseline.py --write --force --reason UX-789
wrote 568 finding(s) to .../tests/quality_baseline.json; 2 authorised by UX-789
```

Squashed the interim commit back (`git reset --soft`) so the net diff
is one `forced` batch added, `findings` unchanged. Post-commit:

```console
$ python3 tools/dev_baseline.py --check
still forced by UX-789: ruff S603 tools/dev_mutation.py (#1) return subprocess.run(argv, cwd=REPO, text=True, capture_output=True, **kw)
still forced by UX-789: ruff S603 tools/dev_sizes.py (#1) run = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
clean: 568 finding(s) match ...; 281 still forced by UX-697; 1 still
forced by UX-744; 2 still forced by UX-762; 1 still forced by UX-781;
2 still forced by UX-789
```

`unknown_keys(document)` refuses a stray key on the document (e.g.
`"forced_by"`) or on a finding (anything but `tool`/`rule`/`file`/
`line`/`nth`), and `do_check` exits 2 naming it before any diff runs.

### Mutations verified red and reverted (2)

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | `unknown_keys` body replaced with `return []` | `TestUnknownKeyIsRefused::test_a_forced_by_key_reds_and_names_itself` | 1 failed, 17 passed |
| M2 | `unknown_keys`' per-entry loop dropped (document-level check only) | `TestUnknownKeyIsRefused::test_a_stray_key_on_a_finding_reds_and_names_itself` | 1 failed, 1 passed (class); 1 failed, 18 passed (file) |

**Deviation.** One verifier hold: the first commit refused a stray key on the document only, not on a finding; the per-entry clause and its guard landed in a second commit (0443f02a). Two commits on the track; one verifier run.
