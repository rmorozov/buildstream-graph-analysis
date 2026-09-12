# Round 114 — the architecture document's last two moves, a walk, and 0.4.1

Run on 2026-09-12.

Round 113 left `UX-689` two chapters from done. This round filed each
as its own row and moved it in a track behind a verifier, serially —
both edit `architecture.md` — ran `UX-685`'s third seeded walk beside
the first track, and cut the release the walk and review 22 had
cleared.

## What closed

- `UX-815` — filed and closed: the ingestion-path chapter (217 lines) into `docs/design/areas/tools.md` as the page's second section. No guard reads inside it — 437 both ways on the blank-and-rerun — so the whole chapter moved; the verifier reproduced the blank-and-rerun, 0 sentences missing.
- `UX-816` — filed and closed: the `bga` area's chapters into `docs/design/areas/bga.md`, a page the area did not have. Four moved; the real-extensions chapter stayed whole, its table read by a guard. 593 → 490 lines outside the verification log. The verifier's blank-and-rerun went red on a docs-wide key guard — the one the Outcome had named.
- `UX-689` — closed with `UX-816`: six moves across five area pages, `architecture.md` 1044 → 490 lines outside the log. The Acceptance Test's "under 400" is not met, and the Outcome says so: the 490 are the skeletons and the log the guards read, not chapters left behind.

- `UX-821` — filed and closed after the merge, on main's own CI: the three adopt jobs (tier reference, touching map, flake ledger) run `dev_tier_drift.py` on a bare interpreter and had been red on `UX-698`'s `defusedxml` import at every push since 2026-09-08 — the gate runs on pull requests, where they never run. Each installs `[dev]` first; a guard reads `ci.yml` for a tool run without its imports, three mutations red.

Filed: `UX-815`, `UX-816`, `UX-817`, `UX-818`, `UX-819`, `UX-820`, `UX-821`.

## Walk, seed 3

The process storm, spine on, cold then incremental, real Chrome, role
R1 in the tools area. Driven on `sonnet`, judged here; the report is
`docs/audits/walk-seed-3.md`. Three findings, each a row: the join
calls a zero-rebuilt run an attribution failure (`UX-817`), two canned
queries error when an element is given (`UX-818`), the export's
Perfetto handoff fetches the trace's JSON quotes as part of the URI
(`UX-819`). One answer-key row: the join on a zero-rebuilt run
recommends nothing.

## Release 0.4.1

Derived, not chosen: the contract state is 0.4.0's byte for byte (25
contracts, the same command set, digest `32a915ff3719`), so the kind
is `patch`. Condition 2, review 22 at 808 closes against the marker
at 537; condition 3, the walk above dated on the candidate commit's
day. Row 813, body generated 537 → 813 (301 lines), tag `v0.4.1` on
the commit that set the version, the three walk findings carried in
the head. The release page on GitHub is the guide's step 8, a click no
tool here makes.

`pymarkdown` reports MD032 once per generated body — the list runs
straight into the closing marker — four blocks, four reports, the
generator's shape since 0.2.0 and outside `make lint`'s document list.
Filed as `UX-820`.

## What the verifiers found

Two runs, two PASS. Neither found what the track's table had not:
`UX-815`'s reproduced the count, `UX-816`'s red guard was already in
the Outcome. Both tracks were mechanical; the verifier's value here
was the independent sentence diff, 0 missing each.

## Standing

The suite's shape, derived by `dev_shape_budget.py` and printed by
`dev_close_task.py --check` (`UX-690`):

```text
shape         files   CI seconds    share
unit            452       821.1s    48.1%
sweep             1         2.1s     0.1%
journey           2         0.1s     0.0%
browser          53       845.2s    49.5%
enormous         20        39.3s     2.3%
total           528      1708.0s
```

## Process, measured

- The box's ruff and pyright were behind main's pins after PR #216: uv's tool shims in `~/.local/bin` shadow `/usr/local/bin`, so `dev_baseline.py --check` was red on a clean tree. The first track spent a stash round trip proving the red was not its own; the fix was `uv tool install --force` for both.
- A bare `git stash` reverted `UX-816`'s work mid-track and a partial checkout gave its verifier a wrong before-snapshot; each caught by its own table, each redone. The stash is the second time this round's shape lost work to it.
- The walk's driving half could not write its report (the Write tool refused the path) and needed three driver scripts to see the quoted `data:` URI; the finding is `UX-819`.
- The release derivation ran while the tracks were open; each merge moved the candidate commit and none moved it past the walk's date.
- PR #222 was rebase-merged: the commit that set the version is `8f238642` on main, not the branch's `1fb8ddb8` the tag named, so the tag guard reddened on main until the tag moved. A release tag is cut on main after the merge, not on the branch before it.
- The session's git gateway answers 403 to a tag push; the tag went up by hand, twice.

## Agents

Five runs — 2 `implementer`, 2 `verifier`, 1 `general-purpose` (the
walk's driving half), all on `sonnet`. The rows are in the ledger.

| | |
|---|---|
| implementer | 2 tracks, both merged behind a verifier; 89k and 187k tokens; 15.6 and 34.5 m |
| verifier | 2 runs, two PASS; 49k and 62k tokens; 12.2 and 10.1 m |
| general-purpose | walk seed 3's driving half; 174k tokens, 8.4 m; three filings |
