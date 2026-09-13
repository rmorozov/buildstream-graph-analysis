# UX-820: the generated release body ends its list on the closing marker

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-252 (the generated body) | **Found by:** round 114, the 0.4.1 cut | **Serves:** the reader of CHANGELOG.md, and `make lint` reading it | **Topic:** docs | **Area:** tools | **Shape:** bounded

## Motivation

`bga release-notes` ends its body on the last closed row's bullet, and
the release guide's writer puts `<!-- /generated -->` on the very next
line — a list with no blank line after it, MD032, a rule
`.pymarkdown.json` enables. Nobody saw it because `lint-docs` lists
`README.md CLAUDE.md REVIEW.md docs/*.md .claude/*.md` and
`CHANGELOG.md` is none of those:

```text
$ python3 -m pymarkdown --config .pymarkdown.json scan CHANGELOG.md | grep -c MD032
4        # one per generated block: 0.2.0, 0.3.0, 0.4.0, 0.4.1
$ git show HEAD~2:CHANGELOG.md > /tmp/prev.md && python3 -m pymarkdown --config .pymarkdown.json scan /tmp/prev.md | grep -c MD032
3        # before the 0.4.1 cut: the shape since 0.2.0, not this release's
```

## Required Fix

`render()` in `tools/bga_release_notes.py` ends the body with a blank
line, the four blocks in `CHANGELOG.md` gain theirs, and `CHANGELOG.md`
joins `lint-docs`' file list so the next release's block is read.

## Out of Scope

- The other three rules the scan reports on `CHANGELOG.md` (MD013,
  MD036 on the older heads) — disabled or house style per
  `.pymarkdown.json`; `UX-109`'s trade holds.

## Acceptance Test

`make lint` reads `CHANGELOG.md` and is clean; mutation: delete the
blank line before one `<!-- /generated -->` — `make lint` red.

## Outcome

Gap measured:

```text
$ python3 -m pymarkdown --config .pymarkdown.json scan CHANGELOG.md | grep -c MD032
4
```

Close measured: `render()` in `tools/bga_release_notes.py` now returns
`"\n".join(lines) + "\n"`, the four generated blocks in `CHANGELOG.md`
each gained the blank line before `<!-- /generated -->`, and
`lint-docs` in the Makefile added `CHANGELOG.md` to its file list.

```text
$ python3 -m pymarkdown --config .pymarkdown.json scan CHANGELOG.md | grep -c MD032
0
$ make lint   # tail
clean: 559 finding(s) match tests/quality_baseline.json; 280 still forced
by UX-697; 1 still forced by UX-744; 2 still forced by UX-762; 1 still
forced by UX-781; 2 still forced by UX-789
[exited with code 0]
```

Mutation table:

| guard | mutation | result |
|---|---|---|
| `test_every_generated_block_ends_on_a_blank_line` (new, in `tests/unit/test_a_release_records_a_contract_state.py`) | drop the blank line before the 0.4.1 block's `<!-- /generated -->` | FAILED — `generated block(s) at index [0] do not end on a blank line`; reverted from the scratchpad copy, then 52/52 passed in both release-guard files |

Same mutation independently confirmed against the real Acceptance Test
tool: `python3 -m pymarkdown --config .pymarkdown.json scan CHANGELOG.md
\| grep -c MD032` read `1` with the blank line dropped, `0` restored.

**Deviation.** None. The touching sweep widened to 529 files on the Makefile edit and took 34 minutes under six tracks; the verifier re-ran it green.
