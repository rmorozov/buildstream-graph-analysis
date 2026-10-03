# Round 168 - the per-element jobserver switches and a docs gap audit, UX-1300

Run on 2026-10-03 from Ruslan's question: how to keep one element out of
`--jobserver auto`, and where that is written. One track, plus a
read-only audit for gaps of the same class.

```text
closed   UX-1300
filed    UX-1301 UX-1302 UX-1303 UX-1304 UX-1305 UX-1306 UX-1307 UX-1308
index    dev_close_task.py --counts: 1257 scenarios, 16 open, 1241 closed
spread   dev_touching.py --spread: 35-199 of 818 test files
```

## What closed

`UX-1300`: `jobserver.md` names the four per-element switches in the
order `_jobserver_injection` reads them, and the four styles; its two
examples run through the code a capture runs.

## Lessons

- The flag inventory that guards guide invocations read only argparse,
  so it called a real `capture run` flag absent: four are consumed out
  of argv first (`UX-1301`). It now reads them by AST, as it reads
  `--schema`.
- Round 167 (#314) shipped with no document; it is waived here by name,
  as 132 and 133 were, because this round's number moved it out of the
  in-progress exemption.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 168 | researcher | sonnet | docs gap audit for UX-1300's thread (UX-1301..1308) | 66k | 24 | 203 s | complete | the flag scan read 41 `--help` outputs, which hide the four translated flags |
