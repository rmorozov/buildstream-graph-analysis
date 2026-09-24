# UX-978: the serial-giant README describes an `auto < off` assertion CI no longer makes

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-910 | **Blocks:** — | **Found by:** architecture review 26 (2026-09-23) — `UX-910` replaced the step's wall-ordering check with `check_jobserver_width.py`, and the example's own README still argues for the check it removed | **Serves:** whoever reads why `bst-examples` passes or fails on `11-serial-giant` | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-910` removed the `awk ... auto < off` step and asserted on width
instead; its guard checks `ci.yml` and nothing else:

```text
$ grep -n "auto < off" tests/unit/test_the_examples_build.py
203:    assert "auto < off" not in body
$ grep -rn "auto < off" --include=*.md --include=*.py . | grep -v "docs/backlog\|docs/audits"
./examples/11-serial-giant/README.md:144:`auto < off` assertion stands on this reading.
./examples/11-serial-giant/check_jobserver_width.py:2:"""UX-910: the step's own check, replacing an unbanded `auto < off`
./tests/unit/test_the_examples_build.py:193:    """UX-910 replaced the `awk ... auto < off` ordering assertion with
```

The README is two paragraphs about that check. `:118-122`, **Risk in
the CI step's own assertion**: "the step's hard `auto < off` check
stands on the CI runner's own quiet reading ... if it reds there too,
that is the finding, and the assertion should drop". `:143-144`: "The
CI step's `auto < off` assertion stands on this reading." It did red
there, and `UX-910` is the row that dropped it: eight off/auto pairs
read -1.4%..+2.2% against a 1% same-sha spread (`ci.yml`'s own comment
on the step). `git log -1 -- examples/11-serial-giant/README.md` is
`90b00507` (`UX-869`), before `UX-910`.

A reader who opens the example to learn what CI checks is told the
opposite of what `ci.yml` runs, and `check_jobserver_width.py`, the
check that is there, appears nowhere in the README.

## Required Fix

Rewrite the two paragraphs as the record they now are - dated, with
the prediction and `UX-910`'s outcome - and say what the step asserts
today: `check_jobserver_width.py` over the two Plane 2 reports and the
auto capture's log.

## Out of Scope

The dated walls and widths, which are records. `examples/README.md`'s
`## 11` section, which names no assertion. The check itself.

## Acceptance Test

```text
grep -n "auto < off" examples/11-serial-giant/README.md   # only inside a dated sentence naming UX-910
grep -c "check_jobserver_width" examples/11-serial-giant/README.md   # >= 1
```

## Outcome

Gap measured (base `ad27b616`): `grep -n "auto < off" examples/11-serial-giant/README.md` hit `:120` and `:144`, both present-tense; `grep -c check_jobserver_width` read `0`.

Close measured:

```text
$ grep -n "auto < off" examples/11-serial-giant/README.md
120:step's then-hard `auto < off` check stood on the CI runner's own quiet
150:`auto < off` assertion stood on this reading until `UX-910` replaced it
$ grep -c check_jobserver_width examples/11-serial-giant/README.md
2
```

Both hits sit in sentences that name `UX-910` and the date; the paragraph now lists the four checks `check_jobserver_width.py` makes. Docs only: no guard added, as the Acceptance Test asks for two greps.
