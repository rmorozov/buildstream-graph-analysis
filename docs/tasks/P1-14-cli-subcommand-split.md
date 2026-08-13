# P1-14: Missing CLI subcommands (`graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics`)

**Priority:** P1 | **Status:** ⚪ Blocked — needs a product decision, not just an implementation | **Depends on:** none

## Spec Reference
Read only: `sed -n '2133,2182p' docs/specification.md` (Part 37 — CLI).
The spec recommends this command structure:
```
bga analyze RUN
bga graph RUN
bga floors RUN
bga replay RUN
bga sweep RUN
bga utilisation RUN
bga diagnostics RUN
```

## Why this is blocked, not just unstarted
The current implementation only has `bga analyze` with flags (`--replay`, `--diagnostics`, etc.) that select which sub-analyses run and appear in one combined report. This is a **legitimate alternative design**, not obviously wrong — it's simpler for users who want "just give me everything" and avoids re-running shared pipeline stages (ingestion, normalization, graph construction) once per subcommand. The spec's recommendation may be aspirational/illustrative rather than a hard requirement — re-read Part 37's exact wording (is it phrased as "MUST" or "recommended structure"?) before assuming this needs a full rewrite.

**Do not implement this without first asking the user (via whatever mechanism your session has for that) whether they want:**
1. The full subcommand split as literally specified (each subcommand runs only its slice, potentially re-deriving shared state, or sharing a cache), or
2. The current `analyze` + flags design kept, with `docs/cli.md` explicitly documenting it as an intentional, spec-compatible deviation (if Part 37's language allows that reading), or
3. A hybrid: keep `analyze` as the primary command, add the other subcommands as thin aliases that call `analyze` with the corresponding flag pre-set (e.g. `bga floors RUN` == `bga analyze RUN --floors-only`), satisfying the letter of the spec's command list with minimal duplication.

## Out of Scope
- Don't add `--cold`/`--allow-partial-cold` here — those are `P1-07`, already scoped as flags on the existing `analyze` command regardless of how this task resolves.

## Acceptance Test
N/A until unblocked. Once a direction is chosen, this task file should be rewritten (or a new one created) with a concrete spec/current-state/required-fix/acceptance-test following the standard template.

## Verification Log
_(N/A — blocked)_
