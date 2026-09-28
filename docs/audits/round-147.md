# Round 147 — the #298 re-review rows close

Run on 2026-09-28 in answer to the owner's #298 re-review at
`156d7436`, four tracks merged in order 1086, 1084, 1085, 1087 and
verified onto `3107b31b`.

```text
closed   UX-1084 UX-1085 UX-1086 UX-1087
index    dev_close_task.py --counts: 1035 scenarios, 22 open, 1013 closed
spread   dev_touching.py --spread: 33-173 of 662 test files
```

## Defects verification found

- UX-1084: a first close keyed safety on flag name alone; the verifier
  found `gcc -l1234` (a linker library) and `curl -O 12345` (an output
  filename via positional inheritance) still kept verbatim. The safe
  set is re-keyed on (binary, option): make/gmake/ninja keep
  `-j`/`--jobs`/`-l`/`--load-average`; a compiler driver keeps only a
  glued `-O<digit>`; `JOBS`/`CMAKE_BUILD_PARALLEL_LEVEL` keep
  regardless. `gcc -l1234` and `curl -O 12345`/`wget -O 12345` now
  pseudonymize (checked: `gcc -lf-9346`, `curl -O f-15243729`).
- UX-1086: the temp-file leak on a write/fsync failure and the
  existing-destination case were fixed and tested.

## Measured

- UX-1085: NFC normalization after casefold added on both sides;
  NFD `café` vs NFC original trips, whole-block and split at the
  combining mark. Deviation: CJK names written back-to-back with no
  separator stay unmatched (pre-existing, same as concatenated ASCII).
- UX-1087: the per-identifier cost is about 1.3 KB (1277 B/id 8->800,
  1311 B/id 800->8000); UX-1069's "~4 MB ceiling" wording corrected.

## Integration

Merged 1086, 1084, 1085, 1087 in that order onto `3107b31b`.
Conflicts only in `tests/quality_reference.json` (re-measured).

## Suite

Full `make test` on `3107b31b`: 10226 passed / 199 skipped / 0 failed.
`make push-check` green.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| implementer | sonnet | file backlog rows UX-1084..1087 from the owner's #298 re-review | 93015 | — | — | — |
| implementer | sonnet | UX-1084 a short numeric credential still exports verbatim | 183780 including one rework after verify | — | — | `gcc -l1234`/`curl -O 12345` leaks came from verification |
| verifier | sonnet | verify UX-1084 | 47139 | — | — | two leaks found |
| implementer | sonnet | UX-1085 the residue scan misses non-ASCII identifiers | 98535 including one rework | — | — | — |
| verifier | sonnet | verify UX-1085 | 67440 | — | — | one leak found |
| implementer | sonnet | UX-1086 the archive publishes before the map is saved | 77512 including one fix pass | — | — | — |
| verifier | sonnet | verify UX-1086 | 37470 | — | — | two defects found |
| implementer | sonnet | UX-1087 the bounded-memory measurement holds identifiers constant | 150165 | — | — | — |
| integrator | sonnet | merge UX-1086, UX-1084, UX-1085, UX-1087 | 80091 | — | — | conflicts only in `tests/quality_reference.json` |
| closer | sonnet | close: row moves, ledger, round document | unknown | — | — | — |
