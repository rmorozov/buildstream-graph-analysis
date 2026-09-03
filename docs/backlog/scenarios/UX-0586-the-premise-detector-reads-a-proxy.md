# UX-586: the premise detector reads a proxy

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-508 (the process bands), UX-403 (the text-scan shape) | **Serves:** the round that reads the process bands | **Topic:** guards

## Motivation

```text
$ python3 tools/dev_process_bands.py --window 20
mutation reddened 80.0 % · non-discriminating guard 20.0 % · deviated 85.0 % · premise false 0.0 %
```

Round 81's own title is "seven premises falsified by measuring".
The detector is a regex (`dev_process_bands.py:47`:
`false premise|premise…(was|is) false`) and misses "the premise is
falsified" (`UX-542:46`), "premise was wrong" (`UX-556:61`),
"premise is half wrong" (`UX-541:53`) — shape 1 of fixing guide §5,
in the tool that measures the process.

## Required Fix

The premise fact becomes a declared line in the Outcome skeleton
(`Premise: held | falsified — <one line>`), written by `--outcome`
and read by the bands tool as a field, not a phrase; the twenty
Outcomes in the window annotated once so the reading is right from
here.

## Out of Scope

- The other three bands — their regexes read headings the skeleton
  already writes.

## Acceptance Test

`--window 20` reports ≥ 7 for round 81's rows; mutation: remove the
declared line from one Outcome — the skeleton guard reds.
