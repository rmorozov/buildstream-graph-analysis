# UX-735: the attachment guide's export size measures a capture not in the tree

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-511 (which set the dated-label shape), UX-195, UX-529 (which bounded the export's data half) | **Serves:** the CI author deciding whether to upload the artifact | **Topic:** docs | **Shape:** bounded | **Area:** tools

## Motivation

Architecture review 18, checklist item 4. `docs/guides/ci-comment.md`
tells a CI author what the attached report costs:

```console
$ sed -n '275,277p' docs/guides/ci-comment.md
it from the run's artifacts and opens it; nothing has to be deployed for
a viewer to exist. Measured on a real 46 s capture with both planes:
**82 KiB**.
```

Two problems, and the second is the one that matters. The figure is
undated, so nothing says which round it was true in. And the capture
it names — "a real 46 s capture with both planes" — is not in the
tree, so no reader and no guard can reproduce it. Six guards cite
this document (`grep -rln ci-comment tests/unit/*.py`); none reads
this sentence.

The only export the repository can measure today is six times it:

```console
$ python3 -c "
from tools.bga_view import export
import pathlib, tempfile
out = pathlib.Path(tempfile.mkdtemp())/'r.html'
export('tests/fixtures/macro_micro/run', str(out))
n = out.stat().st_size
print(f'export bytes {n} = {round(n/1024)} KiB')"
export bytes 499911 = 488 KiB
```

That is a different population — `macro_micro/run` is the repository's
fixture, not the guide's 46 s capture — and it is the point: the
guide's number cannot be checked against anything, and the one number
that can be measured is not close to it. `UX-529` bounded the export's
data half after this sentence was written, and `UX-307`, `UX-342` and
the inlined Perfetto trace all moved what an export carries; a reader
sizing an artifact upload against **82 KiB** is sizing against a tool
that no longer exists.

## Required Fix

Either shape works and the Outcome says which:

- **Date it**, `UX-511`'s shape: keep the 46 s capture's number,
  label it with the round and date it was taken, and say the capture
  is not in the tree. Costs nothing and stays honest; a reader still
  cannot check it.
- **Re-measure on a fixture and derive it**, `UX-549`'s shape: state
  the figure for `tests/fixtures/macro_micro/run`, name the fixture in
  the sentence, and let a guard run `export` and compare. Costs a
  second or two per run and cannot drift.

Prefer the second if the export is cheap enough on that fixture to sit
in a small-tier file; measure it and say. A byte-exact equality will
red on any content change, so bound it — an order of magnitude, or a
band the Outcome argues for — and say what the bound is for.

## Out of Scope

- The export's size itself. Whether 488 KiB is too much for a CI
  artifact is `UX-529`'s axis, not this row's.
- The other figures in `ci-comment.md`. Review 18 read this one
  because it is a measurement; the rest are shapes.

## Acceptance Test

The sentence is either dated with its round or derived from a fixture
a guard measures. Mutation, for the second shape: make `export` write
a materially larger page — the clause reds naming both figures.
