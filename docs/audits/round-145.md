# Round 145 — the anonymized-bundle rows close

Run on 2026-09-28 off `9ec24dd0` (`docs/design/anonymized-bundle.md`),
seven tracks merged and verified onto `fd0bbd9c`.

```text
closed   UX-1060 UX-1061 UX-1062 UX-1063 UX-1064 UX-1065 UX-1067
open     UX-1066 (Low, not scheduled)
index    dev_close_task.py --counts: 1027 scenarios, 22 open, 1005 closed
spread   dev_touching.py --spread: 33-173 of 654 test files
```

## Defects verification found

- UX-1061: the token's length band was capped at 4 chars regardless of
  the value's own band; `k` now starts at the band's own width.
- UX-1067: `gzip.GzipFile(...)`'s FNAME still stamped the output path's
  basename into the header, unguarded by the tar-level fix; closed
  with `filename=""`.
- UX-1062: any `--word` flag name traveled verbatim off any binary
  (a long-flag leak); now kept only from `anonymize.PUBLIC_FLAGS`.
- UX-1062: the exported wall clock started at 0, and `_run_instance`
  reads a 0 start as none, dropping `started_at`; the origin is now
  `bundle.CANONICAL_ORIGIN_US["wall"]`, 2000-01-01T00:00:00Z.
- UX-1063: `expected_output.json` and `with_timeline/analyze.json`
  needed their `elements.fan_in`/`bottleneck.serial_chains` tables
  split into graph order, not name order, after the tie-break rekey.
- `plural()` (UX-1038's helper): the untreated-row refusal's count was
  singular/plural-wrong; fixed at `fd0bbd9c`.

## Suite

Full suite on `2a261e50`: 10132 passed / 199 skipped / 2 failed - one
flaky browser test that passes run alone, one `plural()` mismatch
fixed after (above), both accounted for.

`make push-check` on the commit about to push - see report.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| implementer | opus | UX-1060 every exported value path declares its class | 155524 | — | — | — |
| implementer | sonnet | UX-1061 a pseudonym is keyed, stable, shape-preserving | 68491, rework to 115534 | — | — | length-band fix came from verification |
| implementer | sonnet | UX-1067 the archive and gzip header carry no original metadata | 102367, rework to 123309 cumulative | — | — | gzip FNAME fix came from verification |
| implementer | sonnet | UX-1064 a pseudonym in any text resolves back | 172443, rework to 245951 cumulative | — | — | ships as `bga bundle --resolve`, not a new top-level command |
| implementer | opus | UX-1062 a bundle exports anonymized, refuses a leftover name | 194304, three follow-ups to 230888 cumulative | — | — | flag allowlist and wall origin came from verification and UX-1063's guard |
| implementer | opus | UX-1063 analysis commutes with anonymization | 193246 | — | — | five re-keyed tie-breaks undiscriminated by any capture here |
| implementer | sonnet | UX-1065 a declared public junction keeps its public names | 166431 | — | — | — |
| verifier | sonnet | verify UX-1061 | 67467 | — | — | length-band fix found |
| verifier | sonnet | verify UX-1060 | 203746 | — | — | — |
| verifier | sonnet | verify UX-1067 | 91512 | — | — | gzip FNAME leak found |
| verifier | sonnet | verify UX-1062 | 133369 | — | — | flag-name leak and epoch-0 start found |
| verifier | sonnet | verify UX-1064 | 62723 | — | — | — |
| verifier | sonnet | verify UX-1063 | 88665 | — | — | — |
| verifier | sonnet | verify UX-1065 | 85405 | — | — | — |
| integrator | sonnet | merge the seven anonymized-bundle tracks | 196172 over two passes | — | — | — |
| closer | opus | close: row moves, ledger, round document | unknown | — | — | — |
