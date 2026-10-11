# Walk, seed 5 - 0.6.0 release gate, 2026-10-07, commit 3e3657a7

The 0.6.0 release walk (release guide condition 3). Base `3e3657a7`, 2026-10-07.
Driven on the reporters' model (91k tokens, 26 calls, 2.9 m); judged here: no blocking
finding; 1 and 3 filed, 2 is the cut itself (`UX-1344`), 4 and 5 are seed 4's
bookkeeping lines still open, 6 is seed 4's Escape and Perfetto lines now clean.

```text
seed 5 (unassigned area, R7 release manager, spine on, cold capture, current contract, many population, real Chrome). No `bst` on the box (`which bst` empty), so the committed `tests/fixtures/macro_micro/run` + `plane2.json` (example 06, 11 elements, 2026-08-21) stood in for the capture; no incremental run, no raw trace log, so no timeline and no canned Perfetto queries. `PYTHONPATH=.` set so `bga` imports the worktree.
capture      fixture stamp 2026-08-21 17:01:28 UTC · 11 elements · 9 traced in Plane 2 (813 processes dropped from the fixture) · planes: P1 + P2, trace none
answer key   06 vs optimized/ (diff: core.bst drops `notparallel`; lib chain -> fan-out; codegen only on lib-f): 2 match, 1 partial of 3.
  (1) chain->fan-out: match - correlate "18 edges among 8 elements were measured never-read ... finishes in 19.1 s against 43.2 s".
  (2) codegen over-declared: partial - text says "opened no file staged by 2-7 declared build dependencies each (24 edges across the 7)"; codegen.bst not named there; analyze lists it as "worth nothing to fix today".
  (3) `notparallel`: match - "Remove `notparallel` from core.bst or raise its job count", "`cc1plus` ... 84.5%".
per plane    P1 analyze | "chain-bound ... core.bst 19.1 s -> fixing it saves 12.1 s (26.1% of the build)" | match | yes | none
             P2 correlate | "asked for -j1: remove `notparallel` / raise its job count before touching its sources" | match | yes | none
             P2 capacity | "Lower builders from 4 to 2: the graph binds" | n/a (not in key) | yes | none
page         headline right (chain_bound; core.bst saves 12.1 s, lib-b 4.0, lib-d 4.0) · macro findable (What to fix first, first section) · 868 controls (census counters; 28 classes, 791 in the listed selectors), one driven per class (26 selectors), none differ from label by DOM-delta (copy buttons left no DOM trace; see 5) · 390 px: no horizontal overflow · 500 px Tab,Tab reaches "Sections", Enter aria-expanded "true", Escape returns "false" · console [] csp [] (one NotAllowedError writeText "Document is not focused" when the driver clicked copy buttons headless - harness focus, not scored) · 33 svgs all named, 33 aria-details all resolve · print vs screen: 74 sections / 0 hidden tables both
perfetto     0 canned queries (no timeline in the export: "the raw trace log it was built from was not kept"); added nothing beyond the omitted-timeline sentence
findings     (raw; BLOCKING or non-blocking; verdicts are the judge's)
 1. non-blocking (release guide) → UX-1341 - docs/contributing/release-guide.md step 6 reads `bga release-notes <from> <to>`; the CLI takes flags.
    `bga release-notes 1083 1277` -> "usage: bga release-notes [-h] --from START [--to END]" / "error: the following arguments are required: --from". `bga release-notes --from 1083` -> "194 scenarios closed (closed-row markers 1083 → 1277)." and the grouped body. docs/guides/cli.md is right (`--from START`, required). Site: release-guide step 6.
 2. non-blocking - version: `bga --version` -> "bga 0.5.0"; pyproject.toml:7 `version = "0.5.0"`. Agree; the 0.6.0 bump is pending (UX-1100 "cut release 0.5.0" still listed in release-notes' contracts group).
 3. non-blocking → UX-1342 - seed 4's BLOCKING 1 is changed, not gone. analyze: "23.1 s (50.0% of the build) is what the top 3 are worth together ... That is more than the 16.1 s alone" and `bga whatif --element core.bst --element codegen.bst --element lib-b.bst` -> "saves 23.050s ... individual savings add up to 16.050s" - consistent. Still open: the headline table's top 3 is core/lib-b/lib-d (12.1+4.0+4.0) while "In this order: core.bst (31.1 s) -> codegen.bst (24.1 s, pays off after the step before) -> lib-b.bst", and one line below "codegen.bst (7.0 s) — ... worth nothing to fix today"; `bga whatif --element codegen.bst` -> "43.200s -> 43.200s (saves 0.000s)". The "top 3" is two different triples.
 4. non-blocking - seed 4 carry-over: with no timeline the page keeps `<a id="perfetto-link" href="#" ...>ui.perfetto.dev</a>` and `<a id="trace-download" href="#" download>` (2 `a[href="#"]`), and a "Open timeline in Perfetto" button (census). Visibility not checked.
 5. non-blocking - seed 4 carry-over, copy feedback unobserved: `button.copy-rows`/`copy-sql`/`copy-step` clicks changed nothing in the DOM snapshot (hash, scroll, text length); in headless the clipboard write threw the NotAllowedError above, so whether a failure is shown to the reader is unknown from this drive.
 6. non-blocking - seed 4 items now clean on this run: Escape closes the open Sections toggle (aria-expanded "true" -> "false"); the Perfetto absence sentence and the page agree ("was not kept").
rows added   0 - UX-1342's answer-key row rides its fix; UX-1341 is a guide line, no journey row
friction     `bga release-notes 1083 <count>` as the release guide spells it fails with a usage error, and "closed count" has no one-line source: `dev_close_task.py --counts` prints "1283 scenarios: 6 open, 1277 closed" but the --to marker is the count of closed rows, not the scenario total; found by reading --help. Second cost: worktree shell refused compound `export`/`$VAR` commands without naming the token.
```
