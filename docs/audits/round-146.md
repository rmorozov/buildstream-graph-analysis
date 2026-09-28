# Round 146 — the #298 review rows close

Run on 2026-09-28 in answer to Ruslan's review on PR #298 (credential
values in command lines; unbounded memory in the anonymized export),
four tracks merged in order 1070, 1068, 1069, 1071 and verified onto
`dd90b4df`.

```text
closed   UX-1068 UX-1069 UX-1070 UX-1071
index    dev_close_task.py --counts: 1031 scenarios, 22 open, 1009 closed
spread   dev_touching.py --spread: 33-173 of 658 test files
```

## Defects verification found

- UX-1068: token prefixes (`ghp_`, `glpat-`, `AKIA`, `sk-`), spaced
  flag values, `Bearer` continuations and a mixed-case flag name still
  leaked; a lowercase leading `a=b` was misread as an env prefix. All
  now drop to `<dropped>` and never enter the pseudonym map.
- UX-1070: `build_class` type/variant classed F rendered a literal
  `"None"` key; now A, and an F/G map key drops the entry. A class-C
  map key must be integer-like or the gap check refuses.
- UX-1071: the N/4N timing test was flaky and could not separate the
  scans; replaced by a `start == 0` guard test.
- UX-1069: the Outcome's "archive packed in memory" mutation row was
  overstated; only delaying the write past approval reddens, and only
  the timing test. Corrected at close.

## Measured

- UX-1070: plane2 policy gaps 10 before, 0 after.
- UX-1069: export peak ceiling about 4 MB; archive mode 0600; scratch
  disk about the uncompressed members plus the archive; concurrent
  exports to one path are last-`os.replace`-wins (in spec).
- UX-1071: residue scan 0.22 -> 4.04 MB/s.

## Integration

Conflicts only in `bga/disclosure.py` (`_key_refused` combined into
`step()`) and `tests/quality_reference.json` (re-measured).

## Suite

Full `make test` on `dd90b4df`: 10191 passed / 199 skipped / 0 failed,
476.66 s. `make push-check` green at integration; on the commit about
to push - see report.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| implementer | sonnet | UX-1068 a credential in a command line is dropped, not kept | unknown, one rework after verify | — | — | prefix, spaced-flag and mixed-case leaks came from verification |
| verifier | sonnet | verify UX-1068 | unknown | — | — | four leaks found |
| implementer | opus | UX-1069 the anonymized export runs in bounded memory | unknown | — | — | the archive mutation row was overstated, corrected at close |
| verifier | sonnet | verify UX-1069 | unknown | — | — | — |
| implementer | sonnet | UX-1070 the disclosure policy names what the producer writes | unknown, one fix pass after verify | — | — | build_class A and the C-key check came from verification |
| verifier | sonnet | verify UX-1070 | unknown | — | — | two defects found |
| implementer | sonnet | UX-1071 the residue scan reads a large member in linear time | unknown, one rework | — | — | flaky N/4N timing test replaced by a start==0 guard test |
| verifier | sonnet | verify UX-1071 | unknown | — | — | — |
| integrator | sonnet | merge the four #298 review tracks | 88216 | — | — | — |
| closer | opus | close: row moves, ledger, round document | unknown | — | — | — |
