# UX-922: the adopt route feeds the committed median back to itself, so a reference entry is write-once

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-496, UX-503, UX-803 | **Found by:** round 131 — `UX-908`'s re-record: 36 consecutive adopt commits carried a 2.1x-stale entry at 6.47 while the gate read the file at 13.3-14.5s | **Serves:** every branch charged for a cost `main` carries, and every round that re-records a cell by hand | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-496` made a reference entry the median of a file's last five
readings so that "one afternoon cannot set the number a later run is
judged against". `UX-803` shortened a genuine step to one run by
restarting the samples when the reading and the one before it both
clear `over_gate`. **Neither has ever run on the real document.**
`adopt` takes this run's reading from the candidate's `files`:

```text
tools/dev_tier_drift.py:571   times = candidate.get("files") or {}
tools/dev_tier_drift.py:471   document["files"] = median_low(kept[name])   # record
tools/dev_tier_drift.py:600   document["files"] = median_low(kept[name])   # adopt
```

and the candidate's `files` is already `median_low` of that
candidate's own `samples` — four carried copies of the committed value
rescaled onto the run's clock, plus one real reading. So the median
`adopt` reads back *is* the committed value, and the only number that
can enter `samples` is the number already there.

Run 35664785880's `tier-reference` job log, which is the candidate:

```text
"tests/unit/test_a_drawing_is_graded.py": 6.28,
"tests/unit/test_a_drawing_is_graded.py": [6.28, 6.28, 6.28, 6.28, 13.28],
"spread": {"files": 540, "shift_files": 193, "shift": 0.971, ...}
```

The run read the file at 13.28s. Replayed against the committed
document, `adopt` discards it:

```text
$ python3 -c "...; d.adopt(ref, {'files': cand})"   # cand[K] = 6.28, the real value
after adopt:  files 6.47  samples [6.47, 6.47, 6.47, 6.47, 6.47]
had it carried 13.28: files 6.47  samples [6.47, 6.47, 6.47, 6.47, 13.68]
```

The second line is what `UX-496` was built for, and `UX-803`'s restart
fires on the run after it. The first line is what ships. It matches
`main` exactly: over the 36 commits the adopt job made to
`tests/ci_reference.json` between 2026-09-14 and 2026-09-22, this
entry's five samples only ever held 6.47 and a single 6.48 walking
through the window — the rounding of the carried values, never a
reading.

The population is not one entry. 543 of 566 entries have a full
five-sample window and 399 of those are flat, so every one of them is
frozen at whatever single run first wrote it. That is the mechanism
behind `UX-587`, `UX-716`, `UX-911`, `UX-908` and round 121: five
hand-refreshes of one defect, each read as "the record went stale"
rather than "the record cannot move".

Three documents state the pre-`UX-496` contract as current, and are
accidentally right about the behaviour: `ci.yml:498` ("`--adopt` adds
names the reference lacks and rewrites no entry it holds"), the
`verify` skill ("`--adopt` cannot correct this ... by design") and
`ci_reference.json`'s own note.

## Required Fix

`adopt` reads the reading, not the median: the candidate's
`samples[name][-1]` is that run's own seconds on that run's clock,
which is what `_next_sample` already expects. A candidate with no
`samples` for a name keeps today's behaviour.

The shift is a separate decision and has to be stated rather than
inherited: `ratios` is median-against-median today, which is the
comparison `shift_of` is sized for, and swapping it for
reading-against-median changes what `IMAGE_BAND` refuses. Say which,
with the number.

Then say what the 399 frozen entries are worth: a wholesale
`--record` from one CI run bakes in one sample again (`UX-496`'s own
finding), so the answer is either a bounded number of runs' adoptions
or a refresh that says so in the note.

## Out of Scope

Re-recording any entry by hand — `UX-908` did its one and `UX-912`
owns the refresh. The cross-ref base-carry miss, which is `UX-912`.
Changing `CI_REFERENCE_SAMPLES`, `CI_DRIFT_FACTOR` or
`CI_DRIFT_SECONDS`.

## Acceptance Test

`adopt` on run 35664785880's real candidate puts 13.68 into
`samples` for `tests/unit/test_a_drawing_is_graded.py`, and a second
adoption of a reading over both gates restarts the window at it
(`UX-803`'s own path, reached for the first time).

A guard holds that the value `adopt` takes from a candidate is the
candidate's newest sample: a mutation pointing it back at the
candidate's `files` must redden it, and a mutation taking the *oldest*
sample must redden it too.

`ci.yml`'s comment, the `verify` skill and `ci_reference.json`'s note
say what the route does after the fix; `test_docs_links_and_commands.py`
already reads two of the three.

## Outcome
