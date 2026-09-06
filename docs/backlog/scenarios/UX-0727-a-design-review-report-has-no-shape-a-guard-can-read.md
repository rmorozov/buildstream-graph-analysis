# UX-727: a design review report has no shape a guard can read

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-685 (which gave the walk one), UX-686 (which needs this one) | **Serves:** the release gate, and the round reading a review it did not run | **Topic:** guards | **Shape:** judgement | **Area:** tools

## Motivation

`UX-685` gave the walk a fixed report shape, and
`tools/dev_scenario.py` can therefore recognise one:

```python
_SHAPE = tuple(re.compile(rf"(?m)^{label}\s+\S")
              for label in ("answer key", "per plane", "findings", "friction"))
```

The `design-review` skill has no equivalent. Its template is prose —
*measured → judged → proposed*, a controls table, a numbered findings
list — and the one document in `docs/audits/` that resembles a design
review, `round-90.md`, predates the skill, mixes a process half with a
design half, and names its filings inline (`(UX-667)`, a `## Filed`
paragraph) with no field a guard can anchor on.

`UX-686` wants a release to wait for a review that read its candidate.
It can check the *walk* half today and cannot check the review half,
because there is nothing to recognise.

## Required Fix

The `design-review` skill's report gains a fixed head, on the pattern
`UX-685` set for the walk: enough labelled lines that a regex can tell
one from a round document, and one line naming the findings it filed
so "every finding it filed is closed or declined" is derivable rather
than read by a human. `dev_scenario.py`'s `is_walk_report` is the
model; whether the two share a helper or stay separate is the
decision, and the Outcome says which.

**The decision, taken here: one helper, in a module of its own.**
`UX-686`'s guard is the evidence. It needed the walk's filings and
reimplemented the parse in a test file rather than importing one:

```console
$ grep -n "_FINDINGS_BLOCK\|_FILED" tests/unit/test_a_release_records_a_contract_state.py
345:_FINDINGS_BLOCK = re.compile(r"(?ms)^findings\s+(.*?)^rows added\s")
346:_FILED = re.compile(r"→\s*(UX-\d+)")
$ grep -rn "_FINDINGS_BLOCK" tools/
(nothing)
```

That parse belongs beside the recogniser, and the recogniser is about
*a report under `docs/audits/` with a head a guard can read* — which is
neither the walk's property nor the review's. So: a new
`tools/dev_audit_reports.py` holding the kind→labels table, the kind
recogniser and the filings extraction; `dev_scenario.py`'s
`is_walk_report` and `report_problems` delegate to it and keep their
names, so no caller moves; the release guard imports the extraction
instead of carrying a second copy. `audits_documents()` stays in
`dev_scenario.py` — it is about what the repository *tracks*
(`tracked_paths`, `UX-687`), a different concern from what a document
*is*.

**The head's lines wrap.** `UX-686`'s first date regex read `Base
`<sha>`, <date>.` and found nothing: the walk reports wrap that line
across a markdown line break, so `\s+` rather than a literal space is
what a shape regex needs. Whatever head this item fixes, its guard is
whitespace-tolerant or it is a guard that passes on a rewrap.

## Out of Scope

- The review's *content* — this is about a head a guard can read, not
  about what a review should look at.
- Retrofitting `round-90.md`. **Declined**: it predates the skill, and a head added to it now would be a shape nobody wrote to, which is the drift a fixed shape exists to stop.

## Acceptance Test

A design review report written to the new shape is recognised and its
filed findings extracted; a round document is not. Mutation: drop the
findings line — the guard reds naming the file.
