# Round 121 — the first day on a real project: a FIFO bound onto its own host path, kinds that never read, and the three rows review 24 left

Run on 2026-09-15, after round 120 merged. Eight rows closed: the four
filed from the second field report, review 24's three, and one the
verifiers found on the way. The pull request is #231.

## The premise

The user ran the merged tool on a real project (elements behind a
junction, GNU Make 4.4 on the host) and hit two things on the first
build: `bwrap: can't mkdir parents for .../my_project/.bga/tmp/trace-
*/bind/jobserver: read-only file system` on the first cmake element,
and "bst show gave no element kinds" so every decision read
`unknown_kind`. Two `researcher` reads ground-truthed both: the FIFO is
the one mount `UX-846` never reached, bound onto its own host path and
only under fifo-style auth (make 4.4, never this box's or CI's 4.3);
the kinds read drops every option of the user's own command and, when
it does succeed, keys the map by `bst show`'s junction-qualified name
while the shim looks up the project-relative one. No example has a
junction. Four filings, plus the three rows review 24 left open.

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-869` `UX-870` `UX-871` `UX-866` `UX-867` `UX-868` | disjoint surfaces: the shim's mount, the tracer's read, the map's spellings, the guide's keys, the map's labels, a Chrome case |
| 2 | `UX-872` `UX-873` | after 869 and 871: a junctioned example under `bga snapshot --jobserver auto` in CI; the target read's arity, filed by 870's verifier |

## What closed

| row | what landed |
|---|---|
| `UX-869` | the shim no longer binds the jobserver FIFO onto its own host path; `MAKEFLAGS` and the proxy auth name it under `bind_dst`, where the bind dir already mounts; the `--diagnose` record names both paths; a fake read-only-root bwrap reproduces the field error verbatim |
| `UX-870` | the kinds read carries every global option of the wrapped command by its real arity (read off the installed `cli` group), returns a diagnostic on every path, writes `kinds_read.json` beside `element_kinds.json`, and the warning names the reason and the file |
| `UX-871` | `_parse_element_kinds` stores a junctioned name under both spellings, counts junctions and collisions, and the success record carries both counts |
| `UX-872` | `examples/12-junctioned`, a local junction over one cmake element, built by the `bst-examples` job under `bga snapshot --jobserver auto`; a committed script asserts `core.bst` joins as `cmake` |
| `UX-873` | `_cmd_target` skips a subcommand option's value by a per-subcommand table read off the installed commands: `bst build --deps all t.bst` reads `t.bst` |
| `UX-866` | the coverage walk reads a hint's own nested `properties` under `run_instance`; the guide states 303 keys; `started_at_us` documented |
| `UX-867` | §6's one stale `(open)` label dropped; a guard reads each labelled id's own Status line, and reds on an id with no task file |
| `UX-868` | a real-Chrome case reads a merged edge tick's flush position against its row's rect |

## The verifiers found

- `UX-868`: HOLD - the task file's own mutation table ran two cells
  together, reddening the docs guard, so the pasted touching count
  had never been clean; split and re-measured, re-check PASS.
- `UX-869`: PASS; the two new diagnostics fields had no guard (forcing
  both to `None` at the call site passed 153) - a case through the
  real shim added at merge.
- `UX-870`: PASS; the arity table complete against bst 2.8.0 but only
  `-o` and `--config` exercised (a guard derived from the installed
  group's own `params` added at merge); `--deps all` still misread by
  `_cmd_target`, filed as `UX-873` and closed in the same round.
- `UX-871`: PASS; the Required Fix's count clause left undone and
  undisclosed - wired into `kinds_read.json` at merge, after `UX-870`.
- `UX-866`: PASS; of the eight keys the walk gained only
  `started_at_us`'s prose is load-bearing; a generic walk would have
  added 171 undocumented internals.
- `UX-867`: PASS; an `(open)` label naming an id with no task file
  passed silently - a case added at merge.
- `UX-873`: PASS; `bst source track --deps all` still reads `all`
  (`track` in the target set from `UX-842`), noted, not filed.
- `UX-872`: PASS; the verifier ran the example for real (`EXIT=0`,
  `core.bst` joined as `cmake`) and read `make lint` red on the base -
  the untyped parser return this session's own `UX-871` merge wiring
  introduced, typed before the merge.

## Agents

18 runs this round, every one a row in the ledger, plus review 24's
own row that round 120's ledger missed: two `researcher` reads before
the filings, eight `implementer` tracks and eight `verifier` reads,
all on `sonnet`. Two tracks were resumed once (`UX-868` for its table
row, `UX-872` when the box ran out of disk); one verifier held.

| role | runs | tokens | calls | minutes |
|---|---|---|---|---|
| researcher | 2 | 142k | 81 | 8 m |
| implementer | 8 | 1596k | 959 | 205 m |
| verifier | 8 | 649k | 403 | 126 m |

## The pair

`examples/11-serial-giant`, `--builders 4 --jobserver auto --diagnose`,
`--jobserver-auth fd` then `fifo`, cold caches, a quiet box
(`r121/fifo_pair.py`):

```text
fd:   rc=0   elapsed=260.7s
fifo: rc=255 elapsed=220.9s
Verdict: NOT COMPARABLE - the candidate build failed (giant.bst; 1 built)
```

The fifo sandbox opened (`The bwrap shim ran 1 time(s); 1 rewritten`,
no `mkdir parents` line in 239 log lines; the `--diagnose` record names
`<project>/.bga/tmp/trace-*/bind/jobserver` and
`/tmp/.bst-native-trace/jobserver`), and the sandbox's GNU Make 4.3
stopped on `invalid --jobserver-auth string 'fifo:...'`. The bind
defect the user hit is gone on this box; what fifo-style auth buys
needs a 4.4 host, the user's.

## The gate

| run | head | result |
|---|---|---|
| 0 | `a29ca6b5` (the filings) | 8810 passed, 83 skipped, 1084.92 s |
| 1 | the close | the run this commit is pushed under; the pull request carries the figure |

## Standing

The box ran out of disk once mid-round: 9.9 GB of pytest temp
directories under `/tmp/pytest-of-root` from every sweep this session
ran, plus the pair runs' caches; the `UX-872` track stopped
uncommitted on `0MB free` and resumed after the delete. The user's
16-core host has not yet run the merged fifo path; that reading, and
the llvm-shaped gain the mode exists for, are the next round's premise.
