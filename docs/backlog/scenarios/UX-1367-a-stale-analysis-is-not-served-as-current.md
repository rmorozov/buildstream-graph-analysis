# UX-1367: an analysis written by an older bga is not served as the current one

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the walk of the freedesktop-sdk field-test branch (2026-10-30) | **Serves:** R1 | **Topic:** analysis | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** tests/unit/test_a_stale_analysis_is_not_served_as_current.py

## Motivation

`bga view /home/claude/fdsdk-cap/run` on the published capture serves the
capture's own `analyze.json`, written by bga 0.5.0 in the capture job, so
none of UX-1357..1366 appear and the status line still says "Plane 2 not
captured". Only `--reanalyse` shows the current tool's answer. A reader
of a published capture meets the old tool and cannot tell.

## Decomposition

Input classes: a run dir whose `analyze.json` carries an older `bga`
version; the same version; none.

## Required Fix

`bga view` (tools/bga_view.py) re-analyses, or says on the page which
bga wrote the analysis and offers `--reanalyse`, when the stored
analysis's version differs from the running one.

## Out of Scope

Migrating stored analyses.

## Acceptance Test

On a fixture whose `analyze.json` names an older version, the page
carries the current analysis or the version notice. Mutation: drop the
version check; the guard reds.

## Decision

- `stale` is also true when the stored producer version differs from this build's (`producer.version_of` on both sides), not only when the contract set moved or the analysis is unstamped. `analysis_source` gains `version_moved` (additive; false for an unstamped capture, which is already stale, and under `--reanalyse`).
- Page sentence for a version-only staleness: "analysed at capture by bga 0.5.0; this is bga 0.6.2, whose analysis may differ \u2014 re-run with `bga view RUN --reanalyse`". A moved contract keeps its existing sentence. No automatic re-analysis (minutes on field-scale runs).
- Dev builds: `bga.__version__` is a static string (`"0.6.2"`), with no `+g<sha>` or `.devN` suffix, so two dev builds of one release compare equal and read current; the version is compared as stored, so a suffixed version would differ. Out of reach of this row: stamping a sha into the version.
- Input classes: older version (stale, sentence), same version (not stale), no `analyze.json` (analysed here, not stale).

## Outcome (2026-11-24)

Gap measured, `with_timeline` fixture `analyze.json` stamped `0.5.0` with this build's contract set, `analysis_source(doc, False)` on `origin/main` vs this commit:

```text
before {'stored_producer': '0.5.0', 'this_build': '0.6.2', 'contracts_moved': [], 'version_moved': None, 'stale': False}
after  {'stored_producer': '0.5.0', 'this_build': '0.6.2', 'contracts_moved': [], 'version_moved': True, 'stale': True}
```

Close measured:

```text
$ python3 -m pytest tests/unit/test_a_stale_analysis_is_not_served_as_current.py tests/unit/test_the_page_says_whose_analysis_it_is.py -q
23 passed
```

`test_the_page_says_whose_analysis_it_is.py`'s "from this build is not stale" case now stamps this build's version (it stamped `0.2.9` and relied on the version being ignored).

Mutation table (`tests/unit/test_a_stale_analysis_is_not_served_as_current.py`, 9 tests; each reverted from a copy):

| mutation | reddened |
|---|---|
| `stale` drops `or version_moved` | 2 failed, 7 passed |
| `version_moved` forced false | 2 failed, 7 passed |
| `analysisSentence`'s version branch off | 1 failed, 8 passed |
| unstamped capture counted as version moved | 1 failed, 8 passed |
| `stale` always true | 3 failed, 6 passed |
