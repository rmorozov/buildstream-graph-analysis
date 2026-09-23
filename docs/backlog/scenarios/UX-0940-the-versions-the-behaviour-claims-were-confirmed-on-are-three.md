# UX-940: the repository's BuildStream behaviour claims are pinned to three versions and nothing says which were re-confirmed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-571 | **Blocks:** — | **Found by:** round 136 — reading the durable version claims while filing `UX-939`, after CI's binary moved to 2.8.1 | **Serves:** whoever reads a BuildStream behaviour claim in this codebase and has to decide whether it still holds | **Topic:** guards | **Area:** bga | **Shape:** judgement

## Motivation

`UX-939` argues that the durable form of a version claim is what a
version *publishes*, because that is checkable by anyone against any
binary of that version. The repository has such claims, and they name
two different versions:

```text
$ grep -rn "BuildStream 2\.[0-9]\.[0-9]" bga/ tests/unit/ --include=*.py
bga/artifact_weight.py:5          BuildStream 2.8.0 publishes no such number
bga/cache_capacity.py:7           the cheapest exact source BuildStream 2.8.0 has
bga/cache_effectiveness.py:226    BuildStream 2.8.0 publishes ...
bga/schemas.py:2928               BuildStream 2.8.0 has no artifact size
tests/unit/test_an_artifact_has_a_weight.py:4   2.8.0 publishes no per-element figure
bga/structural/serialization_points.py:10   re-checked against a real BuildStream 2.7.0 install
bga/ingest/models.py:16           get_unique_key() returns a constant - confirmed via BuildStream 2.7.0
```

The two 2.7.0 lines are load-bearing behaviour claims, not history.
`serialization_points.py` asserts that `max-jobs` is a protected
project-wide base variable an element may not redefine and that
BuildStream never reads `max-jobs` from `public:` — the whole module
exists because of what that rules out. `models.py` asserts that a
`stack` element's `get_unique_key()` returns a constant, which is why
`stack` is in the closed list of kinds the analysis flags.

Both were confirmed on 2.7.0, and `UX-939` re-read both in 2.8.1's own
wheel before moving the pins:

```text
buildstream/plugins/elements/stack.py   def get_unique_key: return 1
                                        BST_ELEMENT_HAS_ARTIFACT = False
buildstream/element.py:3103             for var in ("project-name",
                                          "element-name", "max-jobs"):
                                        "invalid redefinition of
                                        protected variable"
grep max-jobs, whole wheel           no read of it from `public:`
```

**They hold.** The row is not that the claims are wrong; it is that
nothing in the tree records that anyone checked. The same two sentences
read identically whether they were re-confirmed today or never since
round 31, and nothing will notice on 2.8.2.

`UX-939` met the cost of that directly. The natural place for the
record is beside each claim, and `bga/structural/serialization_points.py`'s
module docstring is already 36 lines against the register's 25, which
older files may only shrink — so the re-read went into a task file's
Outcome instead, which is the one place a later round will not think
to look. `bga/ingest/models.py` had room and now names both versions.
A record with no cheap home is the argument for giving it one.

That the claims are *stated with* their version is right, and better
than the exercised line `UX-939` is about, because a reader can check
them. What is missing is any record of which have been re-checked
since, so today the answer is "read the git log and guess".

## Required Fix

Say, once and in one place, which BuildStream version each behaviour
claim was last confirmed against, in a form a guard can read, and what
happens when the runner's version moves past it — a warning that names
the unre-checked claims is enough; a red that nobody can clear is what
`UX-939` is filed against.

`UX-939` has already done the re-checking once, by hand, for two
claims. What is missing is the place to put it and the thing that asks
again.

## Out of Scope

`UX-939`'s exercised line and its guard, which is the other half of
this and has to be decided first: this row's "in one place" should be
whatever that decision leaves. Re-checking every fact in
`docs/spec/ingestion-pipeline.md`.

## Acceptance Test

A reading, pasted with its command, of each behaviour claim against the
BuildStream version CI runs, with a stated verdict per claim; and a
guard that reddens when a claim's recorded version is older than the
binary the tier ran on, with a mutation that ages a claim reddening it.

## Outcome

**Round 138, 2026-09-23**

**The gap.** Seven lines in `bga/` and one test name a BuildStream
version for a behaviour claim; none records when it was last checked.
They read on three versions (2.7.0, 2.8.0, 2.8.1) against CI's pinned
2.8.1.

**The close.** `tests/bst_claims.json` holds ten claims at twelve sites:
each with a one-line claim, a `path` and an `anchor` sentence,
`confirmed_on`, and `read` (where that version's wheel says it).
`tests/unit/test_a_behaviour_claim_names_the_bst_it_was_read_on.py`
compares `confirmed_on` with `ci.yml`'s `BST_VERSION` through `UX-939`'s
own `pinned()`, and a claim older than the pin is an
`UnconfirmedBehaviourClaim` in pytest's warnings summary, naming its id
and `path:line`. The register going stale against the tree is a red: a
lost anchor, or a file in `bga/` that names a version with no site.

**The reading**, in 2.8.1's own wheel
(`pip download --no-deps "buildstream==2.8.1"`, sha256 `aa3412eb…9701`;
extracted with `python3 -m zipfile -e`, then one `grep -n` per
register row's `read` location; the middle column is that output):

| claim | 2.8.1 source | verdict |
|---|---|---|
| `max-jobs` is protected | `element.py:3103,3112` refuses a redefinition | holds |
| `max-jobs` never read from `public:` | public `bst` reads: integration-commands, overlap-whitelist, split-rules; 0 lines pair `max-jobs` with `public` | holds |
| `notparallel` is the one control, sets 1 | `_variables.pyx:288-289` | holds |
| `stack` key is constant, no artifact | `stack.py:110` `False`, `:140` `return 1` | holds |
| no published artifact size | `cli.py` 17 format keys, 0 name a size; `widget.py:468-469` prints `files._get_digest().size_bytes`; `_casbaseddirectory.py:581` that digest is the root proto's `SerializeToString()` | holds |
| artifact ref path | `_context.py:344`, `element.py:3464` | holds |
| CAS object path | `_cas/cascache.py:326` | holds |
| quota default and 1024-based sizes | `userconfig.yaml:39,42,45`; `utils.py:901-902` | holds |
| `buildstream2.conf` then `buildstream.conf` | `_context.py:278` | holds |
| `list-contents --long` lists every file | `widget.py:987` | holds |

All ten hold on 2.8.1, so every `confirmed_on` is 2.8.1 and the guard
warns nothing today.

| # | mutation | result |
|---|---|---|
| M1 | `max-jobs-is-protected` aged to 2.7.0 | warns: `1 BuildStream claim(s) last read before ci.yml's 2.8.1 … max-jobs-is-protected (2.7.0) bga/structural/serialization_points.py:12`; same under `-n 2` |
| M2 | `may not redefine` → `must not redefine` in `serialization_points.py` | red: the site clause names the lost anchor |
| M3 | `BuildStream 2.7.0` added to `bga/blast.py`'s docstring | red: `add these claims to bst_claims.json: ['bga/blast.py']` |
| M4 | `<` → `<=` in `unconfirmed()` | red: the self-test, which ages one copy of the register |
| M5 | `BST_VERSION` → 2.9.0 | warns all ten, by id and line |

Each was reverted from a snapshot and the file went green (5 passed).

**Deviations.**

1. The Acceptance Test says the guard *reddens*; the Required Fix says
   a warning is enough and a red nobody can clear is what `UX-939` is
   about. This warns. The suite had no warning channel
   (`grep -rnE "warnings\.warn|pytest\.warns" tests/` → 0), so the
   channel is pytest's own warnings summary, which survives `-n auto`.
2. The completeness clause reads `bga/` only, per file. `tools/` carries
   14 more versioned lines in 8 files, filed as `UX-990`.
3. `artifact_weight.py` cites `element.py:3456`, 2.8.0's line; 2.8.1's
   is 3458-3464. The claim holds and the text says 2.8.0, so it stays.
4. "Never read from `public:`" was read in BuildStream's core, not in
   `buildstream-plugins`.
5. The fixing guide's §6 entry says `(UX-940 (open))`; the `(open)`
   drops when the row moves.
6. The guard walks `bga/`, and no module it names selects it, so CI
   reddened `test_every_derived_census_guard_is_declared` on
   `72716604`. It is census now (`tests/tiers.py`). The census went
   31 -> 32, its bound and `CENSUS_FLOOR` moved with it, `HANDFUL`
   went 45 -> 46 by its stated `census + 14` formula, `WIDE` is
   unchanged, and the spread is 32-164. The 32 census files ran 1562
   passed, 3 skipped in 34.79s at `-n auto`, load 3.40.

`make test-touching`: 84 file(s) selected · 2420 passed, 4 skipped in
234.49s. `make lint` clean. No local `make test`: CI's matrix is the
gate this round (Ruslan, 2026-09-23 08:43).
