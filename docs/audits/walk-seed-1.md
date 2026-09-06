# Walk, seed 1 — round 97

`UX-685`'s first seeded walk. Driving on the reporters' model, judging
on the session's. Base `4a6290b`, 2026-09-06.

```text
$ python3 tools/dev_scenario.py --seed 1
area bga/replay · role R7 (release manager) · Plane 2 absent · cold ·
current contract · population 1 · reader real Chrome
```

```text
seed         1
capture      20260906T021341Z · 3 elements (runtime, one.bst, all.bst) ·
             1 process · Plane 1 only — via `bga wrap`+`bga extract`, not
             `bga snapshot`; see finding 2 for why
answer key   1. one buildable element in a 3-stage chain → 100% chain-bound,
                zero slack, no scheduler contention (widest stage = 1)
             2. Plane 2 genuinely absent → every surface prints the *same*
                one absence sentence, never null or silent
             3. `bga correlate` must refuse, not emit a partial join
per plane    1 | "chain-bound, not scheduler-bound: the critical path is
             100%..." — byte-identical in the CLI and the page headline |
             match | yes, names one.bst | none
             2 | "Plane 2 was not captured for this run, so there is no
             per-process detail. `bga snapshot -- bst build TARGET` captures
             both planes." — identical in the JSON field, stderr and the
             export | match | yes, names the fix | none
             correlate | "Error: no Plane 2 report given, and none beside
             run..." exit 2 | match | yes | none
page         headline right — `#headline` byte-identical to the CLI's Key
             Findings sentence. Macro findable by rail; **unclear** by the
             jump box: typing `run`/`one` changed no listbox the walker could
             find. 451 controls in 26 classes; one instance per class driven,
             19/26 changed visible state, 7 are plain anchors that navigate.
perfetto     0 of 17 canned questions answered — no timeline in this export
             (`has_timeline: false`, omitted for the stated Plane 2 absence).
             Consistent with the guide's Plane-2-only gating; nothing to add.
findings     1. `dev_scenario.py`'s recipe names `bga gen-synthetic --seed N
                --elements 1`; the flag does not exist (`unrecognized
                arguments: --elements`), and `--layers/--width` plants a run
                rather than building the project the next recipe line builds.
                → UX-723
             2. The recipe's `bga snapshot -- bst build all.bst` is printed
                for both "no hook, no spine" and "the LD_PRELOAD hook, no
                spine" — one command, two annotations, neither what it does;
                snapshot defaults to `--trace-opens --trace-spine=auto` and
                captured Plane 2 anyway. `--no-trace-opens` and
                `--trace-spine off` exist and neither row names them. → UX-723
             3. `NotAllowedError: ... Clipboard: Document is not focused`
                during a batched click sequence, not reproduced on an isolated
                click. **Judged: not a defect** — a headless-focus artefact of
                firing many clicks in one CDP round-trip. Not filed.
rows added   1 — `test_a_scenario_is_named_by_its_seed.py`, not the
             journey's key: the finding is about the walk's own tooling,
             not about what a build report promises. The clause records
             that the recipe's `gen-synthetic` line does not parse.
friction     Reaching a genuinely Plane-2-absent capture. The recipe's own
             annotation was false against the tool as built, forcing a detour
             through the `wrap`/`extract` path `cli.md` treats as legacy.
             Driving ledger 156,932 tokens — **over** the skill's 100k target.
```

## Judging

Findings 1 and 2 are one defect with two faces and are filed as
`UX-723`: the tool `UX-685` landed prints a script that does not run.
That the first walk found it in its first minute is the strongest
evidence available that the walk verifies what the guards cannot —
`dev_scenario.py` has nine passing clauses and none of them runs a
command it prints.

Finding 3 is judged out. The walker was right to record it raw and
right not to resolve it.

**The 100k driving target was missed by 57%.** Both seeds' ledgers are
in `UX-685`'s Outcome; the target stands as written and is not met.
