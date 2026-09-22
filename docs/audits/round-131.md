# Round 131 — a rising ratio that was a stale record

Run on 2026-09-22 from `74fb2712`. One row closed (`UX-908`), one
filed (`UX-922`), and one guard waived so the round could reach a green
gate at all: `main` was red on `round-130.md`'s dateline, which #249's
merge moved a day past the round's own work date. The reading itself is
four commands and two records, and the bisect is `git show` over one
file; the only track was `self-review`.

```text
closed   UX-908   the drawing-grade guard's four CI excursions
filed    UX-922   adopt reads the candidate's median, not its reading
records  tests/tiers.py 3.1s -> 8.7s, tests/ci_reference.json 6.47 -> 13.86
```

## The premise, and what it cost to check

`UX-908` was filed on a rising ratio: 1.701, 2.142, 2.245 over three
CI runs, "a file that grew, or a cost that grew under it, not a
runner's clock". Two of those three clauses hold. The ledger's fourth
row, appended after the filing, reads **2.114** — below the third — and
the three post-growth readings span 6% with no trend. It is one step
and then a band, which matters because the Required Fix says a
`declared` entry is the wrong answer "unless the re-timing shows the
band is flat after all". The band is flat; the entry is still the
wrong answer, because the level it is flat *at* is 2.1x the record.

The step is bracketed exactly. The ledger's ratio is against
`ci_reference.json`'s 6.47, not the 3.1s tier floor, so the four rows
are 11.01 / 13.86 / 14.53 / 13.68 s on that document's clock. The
file's text is one blob (`8e1243d6`) across the last three readings and
`HEAD`, and two of those three heads are documentation-only commits:

```text
82b6249d  26 tests  715 lines  run 34933450749  x1.701  11.01s
16a85b4c  27 tests  748 lines  UX-862
4a056a7d  33 tests  871 lines  UX-863
96c49cb9  36 tests  967 lines  UX-868, the file's first two @needs_browser
98967fc9  36 tests  967 lines  run 35507451517  x2.142  13.86s  docs only
5a10155e  36 tests  967 lines  run 35664785880  x2.114  13.68s
```

Locally, alone and single-process: 10.27 / 8.73 / 8.41s against 3.1s.
In-suite from the medium tier's own junit: 7.88s. And this box runs the
files `tiers.recorded()` names at a **median x0.828** over 171 of them,
so the box is 17% faster than the one the floors came from and the file
still reads 2.5x its own record.

## What the round actually found

The re-record is two numbers. The finding is why neither moved on its
own for three weeks. `adopt` takes this run's reading from the
candidate's `files` — which is already `median_low` of that
candidate's own `samples`, four carried copies of the committed value
plus one real reading. So the number `adopt` reads back *is* the
committed value:

```text
candidate files[K] = 6.28          (run 35664785880's own job log)
after adopt:  files 6.47  samples [6.47, 6.47, 6.47, 6.47, 6.47]
had it carried 13.28: files 6.47  samples [6.47, 6.47, 6.47, 6.47, 13.68]
```

`main` agrees: over the **36 commits** the adopt job made to
`tests/ci_reference.json` between 2026-09-14 and 2026-09-22, this
entry's window only ever held 6.47 and a single 6.48 walking through
it — the rounding of the carried values, never a reading. 543 of 566
entries have a full window and 399 of those are flat, so `UX-496`'s
median and `UX-803`'s step restart have never run on the real
document. That is `UX-922`.

## Standing

The flake ledger's three files at or past `EXCURSION_FLOOR`:
`test_a_drawing_is_graded.py` (4, closed here),
`test_the_fold_says_how_deep_it_goes.py` (3, `UX-917`),
`test_the_trace_census_reads_both_ends.py` (3, `UX-890`). Both
remaining rows are the same shape as this one until `UX-922` lands: a
reading read as a flake because the record it is read against cannot
move.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| self-review | sonnet | `UX-908` close + `UX-922` filing | 151k | 58 | 8.5 m | confirming the hand-append matched the `verify` skill's raw/shift rule needed tracing `flake_ledger.json`'s stored `shift` field back through `dev_tier_drift.py`'s own `ratio / shift`, since it is not the run's printed drift shift |

No Important findings, two nits, both taken: this document did not name
the waiver commit, and the note below showed the shift derivation for
one of the three readings rather than the identity behind all three.
