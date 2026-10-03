# Round 168 - the per-element jobserver switches and a docs gap audit, UX-1300..1312

Run on 2026-10-03 from Ruslan's question: how to keep one element out of
`--jobserver auto`, and where that is written. One track and a
read-only audit for gaps of the same class, then the audit's eight rows
as seven tracks, then two rows from the owner's own junctioned element.

```text
closed   UX-1300 UX-1301 UX-1302 UX-1303 UX-1304 UX-1305 UX-1306 UX-1307
         UX-1308 UX-1311 UX-1312
filed    UX-1301..UX-1312; UX-1309 UX-1310 stay open
index    dev_close_task.py --counts: 1261 scenarios, 10 open, 1251 closed
spread   dev_touching.py --spread: 35-204 of 827 test files
```

## What closed

`UX-1300`: `jobserver.md` names the four per-element switches in the
order `_jobserver_injection` reads them, and the four styles; its two
examples run through the code a capture runs.

- `UX-1301`, `UX-1302`: the four translated capture flags print in
  `capture run --help`, and `bga snapshot` forwards them.
- `UX-1303`, `UX-1305`..`UX-1308`: `.bga/config`, zero-process
  troubleshooting, run-store growth, every flag named, the graph
  owner's guide.
- `UX-1304`: a kind outside the shipped table joins through its
  declared `bga-jobserver-env`; a NAME BuildStream already sets blocks
  injection.
- `UX-1311`: an annotation on a junctioned element reaches the shim,
  which names it without the junction.
- `UX-1312`: `--jobserver-auth-override @PATH` reads its groups from a
  file, for `capture run` and `snapshot`.

## Lessons

- The flag inventory that guards guide invocations read only argparse,
  so it called a real `capture run` flag absent: four are consumed out
  of argv first (`UX-1301`). It now reads them by AST, as it reads
  `--schema`.
- Round 167 (#314) shipped with no document; it is waived here by name,
  as 132 and 133 were, because this round's number moved it out of the
  in-progress exemption.

- Ruslan's annotation did not take: `bst show %{public}` showed no
  `bga:` key on a junctioned element. Separately, bga keyed the map by
  the junction-qualified name and the shim looks up the short one, so
  it could never have matched (`UX-1311`). Element kinds had the fix
  since `UX-871`; the auth map, built beside them, did not share it.
- UX-1304's verifier failed it twice: the first fix widened a `-j1`
  element, the second still set other declared NAMEs. Every argv mix of
  declared and composed names, enumerated before the first commit,
  would have saved both.
- Two merge-time findings the tracks' guards passed: an inline `#` in
  an override file read as a glob, and the guide's file example used a
  junction-prefixed glob that, after `UX-1311`, matches nothing.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 168 | researcher | sonnet | docs gap audit for UX-1300's thread (UX-1301..1308) | 66k | 24 | 203 s | complete | the flag scan read 41 `--help` outputs, which hide the four translated flags |
| 168 | implementer | sonnet | UX-1303 .bga/config section | 49k | 34 | 444 s | merged | see round-168 |
| 168 | implementer | sonnet | UX-1303 fix loop | 61k | 19 | 203 s | merged | see round-168 |
| 168 | verifier | sonnet | UX-1303 verifier | 34k | 11 | 123 s | complete | see round-168 |
| 168 | implementer | sonnet | UX-1308 graph owner guide | 71k | 39 | 621 s | merged | see round-168 |
| 168 | implementer | sonnet | UX-1308 fix loop | 85k | 10 | 205 s | merged | see round-168 |
| 168 | verifier | sonnet | UX-1308 verifier | 41k | 22 | 132 s | complete | see round-168 |
| 168 | implementer | sonnet | UX-1307 flags named in cli.md | 92k | 39 | 653 s | merged | see round-168 |
| 168 | implementer | sonnet | UX-1307 fix loop | 107k | 54 | 1047 s | merged | see round-168 |
| 168 | implementer | sonnet | UX-1307 fix loop | 132k | 17 | 336 s | merged | see round-168 |
| 168 | verifier | sonnet | UX-1307 verifier | 56k | 30 | 157 s | complete | see round-168 |
| 168 | implementer | sonnet | UX-1305, UX-1306 real-project guide | 101k | 76 | 1271 s | merged | see round-168 |
| 168 | implementer | sonnet | UX-1305, UX-1306 fix loop | 118k | 28 | 282 s | merged | see round-168 |
| 168 | verifier | sonnet | UX-1305, UX-1306 verifier | 49k | 21 | 118 s | complete | see round-168 |
| 168 | implementer | opus | UX-1301, UX-1302 help and snapshot | 132k | 113 | 1709 s | merged | see round-168 |
| 168 | verifier | sonnet | UX-1301, UX-1302 verifier | 44k | 19 | 150 s | complete | see round-168 |
| 168 | implementer | opus | UX-1304 declared jobserver env | 118k | 83 | 855 s | merged | see round-168 |
| 168 | implementer | opus | UX-1304 fix loop | 153k | 35 | 524 s | merged | see round-168 |
| 168 | implementer | opus | UX-1304 fix loop | 168k | 16 | 385 s | merged | see round-168 |
| 168 | verifier | opus | UX-1304 verifier | 54k | 22 | 191 s | FAIL | widened a -j1 element; see round-168 |
| 168 | verifier | opus | UX-1304 re-verify | 66k | 12 | 130 s | FAIL | other declared NAMEs still set |
| 168 | verifier | opus | UX-1304 re-verify | 72k | 8 | 83 s | PASS | see round-168 |
| 168 | implementer | sonnet | UX-1311 junctioned annotation | 52k | 26 | 427 s | merged | one unguarded clause, guarded at merge |
| 168 | verifier | sonnet | UX-1311 verifier | 34k | 18 | 415 s | PASS | see round-168 |
| 168 | implementer | sonnet | UX-1312 overrides from a file | 69k | 42 | 477 s | merged | two edge cases fixed at merge |
| 168 | verifier | sonnet | UX-1312 verifier | 56k | 33 | 499 s | PASS | inline `#` and a spaced path; see round-168 |
