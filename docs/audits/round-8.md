# Audit round 8: `UX-64` at real scale, and the guard that is now the blocker

Run [`32055047259`](https://github.com/rmorozov/buildstream-graph-analysis/actions/runs/32055047259),
`bga` at `835e3d9` (the `UX-64` commit), `freedesktop-sdk` at `953683fb`,
BuildStream 2.7.0, 4-core runner, `--builders 4 --max-jobs 4`. Traced
build exit 0. Published to `captures/fdsdk-latest` as `66a97e1`.

## The headline: element attribution went from 14.9% to 86.1%

| | round 7 | round 8 |
|---|---|---|
| sandboxes resolved | 6 of 25 (one via unsound elimination) | **9 of 25**, all sound |
| ambiguous / conflicting / unmatched | 18 / 1 / 0 | **16 / — / 0** |
| `intervals_used` | (not available) | **true** |
| processes relabelled | 19,024 | **109,873** |
| **processes correctly named** | 19,024 / 127,629 (**14.9%**) | **109,873 / 127,629 (86.1%)** |
| resolved names valid in the declared graph | — | **8 of 8** |

`unmatched: 0` held at real scale, which was the risk `UX-64` flagged:
the end-edge rule could have pushed sandboxes out of every span. It did
not.

Note the shape of the win. Only 9 of 25 sandboxes resolved, but they
carry 86.1% of the processes — the resolved ones are the *heavy*
elements. The 16 that remain ambiguous are the short ones at the start of
the build, where four spans open simultaneously and a two-second sandbox
fits inside all of them. Resolving the elements that matter is exactly
the useful half.

## What that unlocked

**`UX-46` declared-vs-used** is now genuinely per-element: **10 unused
candidates and 14 used**, against round 7's 9 and 4.

**`UX-63` peak memory** attributes to real elements for the first time:

```text
components/_private/cmake-stage1.bst   1902.3 MB   measured 10057/11974
components/doxygen.bst                 1491.3 MB   measured   913/1139
components/python3.bst                  365.5 MB   measured 13774/14384
components/bison.bst                    231.4 MB   measured 42728/42804
```

Four concurrent builds of `cmake-stage1`'s shape is ~7.6 GB against this
runner's 16 GB — and `cmake-stage1` is *also* 43.5% of the critical path
(`UX-65`). Two independent signals, same element.

**Steady:** `UX-57` dropped **0** (88,373 paths, 90,777 windows),
`UX-61` `max_concurrency` **60**, `UX-55` `run_mode` incremental,
confidence **0.9996**, no failed hard gates, **0 violations**.

## The remaining blocker: an all-or-nothing reliability guard

`bga correlate` still refuses the join, and its message now contradicts
itself:

```text
NO USABLE JOIN: Plane 2's element attribution is unreliable.
  only 109873 of 127629 traced processes (86.1%) carry a name that looks
  like a BuildStream element; the largest bucket is
  'components/bison.bst' with 42804 processes.
```

`components/bison.bst` **is** an element. The guard is naming a correctly
attributed bucket as evidence that attribution failed, because the rule
is literal:

```python
reliable = bool(by_element) and recognized_processes == total
```

**100%, or nothing.** That was the right rule when the measured answer
was 0.6% and every per-element figure was fiction. At 86.1%, with all
eight resolved names valid and the residue sitting in an explicitly
*unresolved* bucket, it blocks a join that would be correct for the
elements it covers.

Filed as `UX-66`. The fix is not a lower threshold — it is to separate
two different things the guard currently conflates: a name that is *not
an element* (dangerous, refuse) from a process that is *known to be
unresolved* (safe, exclude it and say how much was excluded).

## Round 8's process finding: a cancelled run clobbered a good capture

Run `32053016303` — push-triggered on an older commit — was cancelled
mid-capture when this round's dispatch superseded it. Its publish step
runs `if: always()`, so it published anyway: a 36 KB tarball with a
**0-byte `native-trace.log`** and no `native-report.json`, overwriting
round 7's good capture at the branch tip.

Nothing was lost (round 7 survives in history at `df20544`), but for
~64 minutes the published "latest capture" was a broken partial with
nothing marking it as such. Filed with `UX-66`.

The near-miss is worth naming too: this round's own check-in nearly
audited that broken capture instead of the real one. What prevented it
was checking `capture-context.txt`'s `bga_ref` against the commit the
round was supposed to test — the same discipline that caught the merged-PR
mistake earlier. **Verify the pointer, not just its existence.**
