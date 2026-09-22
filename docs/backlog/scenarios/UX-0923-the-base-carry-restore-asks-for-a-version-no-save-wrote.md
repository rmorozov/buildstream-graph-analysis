# UX-923: the base-carry restore names a path no save wrote, so its cache version never matches

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-803, UX-912 | **Found by:** round 135 — `UX-912`'s cache-scoping half, read against `actions/cache` v6's own source instead of its log lines; filed as UX-922 and renumbered, because #254 took that id 40 minutes earlier (`UX-920`'s shape, third occurrence) | **Serves:** every pull request charged for an excursion `main` already carries | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-912` narrowed `UX-803`'s dead base carry to "cache scoping and
rules out the key and a missing save", on four readings of
`actions/cache` across three refs, and stopped there because the
Actions caches API answers 403 through this environment's proxy.

The narrowing is not supported by its own evidence. In all four
readings the ref and the restore's `path` **co-vary**: every same-ref
restore quoted (`perf-carry-`, twice) names the same `path` its save
wrote, and the one cross-ref restore (`tier-carry-refs/heads/main-`)
names a different one. Ref was never the only thing that changed.

The `path` is the thing that decides, and `actions/cache` v6 says so
in its own source rather than in its log:

```text
dist/restore/index.js  getCacheVersion(paths, compressionMethod, ...)
    components = paths.slice(); components.push(compressionMethod);
    components.push(versionSalt);            # versionSalt = '1.0'
    return sha256(components.join('|'))
dist/restore/index.js  restoreCacheV2:
    request = {key, restoreKeys, version: getCacheVersion(paths, ...)}
dist/save/index.js     saveCacheV2:
    version = getCacheVersion(paths, compressionMethod, ...)   # `paths`,
                                       # not the `cachePaths` it resolved
```

The service matches key **and** version. So the two steps asked for
different entries, computed from the literal `path:` input:

```text
save    path: $RUNNER_TEMP/tier_carry.json
        version d1e90db57d1530e47e162e6b11eaa93f84ca3001ce4a09d2d9c450d492a9ee43
restore path: $RUNNER_TEMP/tier_carry_base.json
        version a3a89e944c9c3fa0c32e5671020d098e3480585e61adb7f68ac41647127d7b4d
```

No key could have hit that. The log never said so: the version is
printed at `core.debug` (`Cache not found for version ${...} of keys`)
and the `info` line the runs recorded — `Cache not found for input
keys: tier-carry-refs/heads/main-, tier-carry-refs/heads/main-` —
drops it, which is why four runs read a key problem.

**And a hit would have been worse than the miss.** `extractTar` is
`tar -xf <archive> -P -C $GITHUB_WORKSPACE` with no member list, so a
restore places every member at the path it was saved from and the
restore's own `path` input places nothing. Reproduced locally with the
action's own arguments:

```text
manifest member          ../_temp/tier_carry.json
tar --posix -cf cache.tzst -P -C $GITHUB_WORKSPACE --files-from manifest.txt
tar -xf cache.tzst -P -C $GITHUB_WORKSPACE
  tier_carry.json      exists: YES
  tier_carry_base.json exists: no
```

The step sits *below* the branch's own restore, so a hit would have
overwritten this branch's carry with `main`'s and left `--base-carry`
reading a file that still did not exist — the branch would then have
agreed with `main`'s runs about its own files.

**A third defect the same fix has to carry.** On the default branch
the two keys are one series, so a working base restore hands a run its
own last carry, and `based_rows` splits off exactly the rows
`repeated` would have confirmed. Measured on one file at 50s against a
2.4s record, with a carry naming it:

```text
--base-carry=absent                 exit=1  1 file(s) slower than CI's own record
--base-carry=same file as --carry   exit=0  1 file(s) ... the base's, not this branch's
```

That is `UX-442`'s two-run rule switched off on `main` — the branch
whose readings every other branch is excused against.

**What is still not known.** Whether a `refs/pull/N/merge` run can
read a `refs/heads/<default>` entry at all. The version mismatch is
*sufficient* to explain every miss on record, so scoping is untested
rather than ruled out; it is now testable, because a restore with a
matching version either hits or does not.

## Required Fix

The base carry keeps travelling by cache — the means was never the
problem — with the three defects above fixed together, because each
one alone leaves the carry unreadable:

- the base restore's `path` is the save's path, so the version matches;
- it runs **before** the branch's own restore, and a step moves the
  restored file to the name `--base-carry` reads;
- it does not run on the default branch.

A guard reads every `*-carry-` cache step's `path`, not only its
`key`, and refuses a restore whose path no save of that family writes.

## Out of Scope

`UX-912`'s reference refresh, which needs a CI run's own
`ci-reference-candidate` artifact — Actions artifact downloads are 403
through this environment's proxy, so it is owner-side. Publishing the
carry as an artifact or committing it, which `UX-912` weighed: the
cache is not the defect. Whether cross-ref cache reads are scoped,
which this fix only makes readable; the Outcome records what the
first run said.

## Acceptance Test

One `test (3.11)` run on a pull request whose log reports a restored
`tier_carry_base.json` rather than `no carry from the base branch's own
runs reachable`, with the `main` run it came from named in the Outcome.

A mutation restoring the base step's own `path`, deleting the step that
places the file, moving the base restore below the branch's own, or
dropping the default-branch condition each reddens a named clause.

## Outcome

## Outcome (round 135, 2026-09-22) — 🟢 Done

**Premise:** held, and it falsifies `UX-912`'s: the restore asked the
service for a cache version no save had ever written.

### The gap, measured

`actions/cache` v6 (`55cc834`), its own source, not its log:

```text
getCacheVersion(paths, method, ...) = sha256(paths|method|versionSalt)
restore/saveCacheV2 both send it, from `paths` - not `cachePaths`
save    $RUNNER_TEMP/tier_carry.json      -> d1e90db57d1530e4..
restore $RUNNER_TEMP/tier_carry_base.json -> a3a89e944c9c3fa0..
```

Placement, with the action's own tar arguments: `tar -xf cache.tzst
-P -C $GITHUB_WORKSPACE` on a member `../_temp/tier_carry.json` leaves
`tier_carry.json` — a hit would have clobbered the branch's own carry.

Third reading, on the tool: a 50s file against a 2.4s record, with
`--base-carry` a copy of `--carry` — what the default branch restores
for itself:

```text
--base-carry=absent                 exit=1  1 file(s) slower than CI's own record
--base-carry=same file as --carry   exit=0  1 file(s) ... the base's, not this branch's
```

### After

The base restore names the save's path, runs before the branch's own,
hands it to a `mv`, is skipped on the default branch, and a step below
the gate says whether a carry arrived; the guard reads `path` now.

```text
$ python3 -m pytest tests/unit/test_a_slow_file_says_which_file.py \
    -k "TestCiSuppliesTheMemoryTheRuleNeeds or TestABaseExcursionIsReportedNotFailed" -q
14 passed, 136 deselected in 0.59s
```

### Mutations verified red and reverted (8)

| # | mutation | reddened |
|---|---|---|
| A1 | base restore's `path` back to `tier_carry_base.json` | `test_a_restore_asks_for_the_version_its_save_wrote` |
| A2 | the `mv` step deleted outright | `test_the_base_carry_is_placed_by_a_step_that_can_place_it` |
| A3 | base restore moved below the branch's own | same clause, its ordering assert |
| A4 | `github.ref != …default_branch` dropped from the base restore's `if:` | `test_the_default_branch_does_not_excuse_itself` |
| A5 | `based_rows` returns no rows | `test_a_base_carry_equal_to_this_runs_own_excuses_everything` |
| A6 | the step saying whether the carry arrived, deleted | `test_the_base_carrys_arrival_is_said_below_the_gate` |
| A7 | that step moved above the gate, beside the `mv` | same clause, its ordering assert |
| A8 | `always()` dropped from it | same clause, its `if` assert |

A2's clause passed A2 as first written: the gate's own `--base-carry
<path>` satisfied "some step mentions it" — the step that *reads* it.

### Deviation

The Acceptance Test's live clause is not satisfiable as written, and
run 35680793877 is why: the gate returns `tiers ok` at
`dev_tier_drift.py:1150`, *before* `--base-carry` is read at `:1155`,
so a clean run prints neither message. Hence A6-A8 — a step *below*
the gate says either way, under `always()`. The tail still missed it,
that job being 6,745 lines against 5,000 served, so the `::notice::`
beside it carried instead, `UX-621`'s route:

```text
$ GET /check-runs/106613117915/annotations     (run 35686105692)
notice | tier carry: the default branch's carry restored
```

That run is `event=pull_request` on #255, so `github.ref` was
`refs/pull/255/merge` reading main's entry: scoping was never it.

`UX-912`'s reference-refresh half is untouched and still owed: it
needs a run's own `ci-reference-candidate` artifact, and artifact
downloads are 403 through this proxy, so only the owner can pull it.
