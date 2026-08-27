# UX-326: the tool's own sentences are contracts

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-218 (the executed-argv precedent) | **Serves:** R1 | **Topic:** cli

## Motivation

Two frictions from the stranger walk, one rule. (F3) `bga analyze`
ends with a good "Next:" block whose third suggestion prints as
`bga snapshot /abs/path/to/project` — run verbatim it crashes
(`ValueError: command must start with 'bst'`) and deposits debris;
the project belongs in `--project`, and the printer forgot its own
parser. `UX-218` made published `next_steps` argvs *executed* in
tests; this printer is evidently a second, unguarded path. (F4)
`bga compare @prev @last` prints "(--allow-mismatch was given;
treat every figure below with real skepticism)" **with no flags
given** — a sentence asserting a flag state that is false, under
the producer-stamp warning. Both are the same defect: printed
sentences that claim things the program state contradicts.

## Required Fix

Every printed command the tool suggests goes through the one
`next_steps` builder whose argvs are executed against fixtures
(the second printer retired); the `--allow-mismatch` sentence
renders only when the flag was actually passed, and the
mismatch-warning's unconditional text says what is true instead.
A sweep for other flag-claiming sentences rides along, with each
gated on its flag.

## Out of Scope

- New next steps — the block's content is right; only its third
  argv is wrong, and this item fixes the printer, not the plan.

## Acceptance Test

Every command string the CLI prints anywhere (collected by the
guard from captured output on fixtures) parses against the real
parser and the suggested ones execute exit-0 (mutation: re-print
the positional-project form → red); compare without the flag
never prints the flag's name (mutation: unconditional print →
red), and with the flag prints it.

## Outcome (round 47, 2026-08-27) — 🟢 Done

### There were three broken sentences, not two

The filing named F3 (`bga snapshot /abs/path`) and F4 (the
`--allow-mismatch` claim). Writing the guard found a **third**, in the
same block and never reported by anyone:

```text
before:  bga snapshot /tmp/…/project
         bga compare @prev @last --project /tmp/…/project

$ bga compare @prev @last --project …
usage: bga [-h] [--version] COMMAND ...
bga: error: unrecognized arguments: --project …
```

`bga compare` has no `--project` and never has. The line has been
printed since `UX-218` and copied into `docs/guides/cli.md`'s worked
example, so a reader following the guide got the same error.

```text
after:   bga snapshot --project /tmp/…/project -- bst build all.bst
         bga compare @prev @last
```

`snapshot`'s positional is `argparse.REMAINDER` — the *build command* —
so the project goes in `--project` and the build after the `--`. The
build itself comes from `run_identity.targets`, which the run has
carried since `UX-07` and which `run_instance` now publishes; with no
targets recorded the step is **not offered at all**, which is the rule
the top of `compute_next_steps` already applies to a missing run path:
a command spelled approximately is worse than no command.

`compare` cannot take a project, so the project moved into the sentence
("run it in …") rather than into a flag that does not exist. Adding the
flag would have been a CLI change, and the filing scoped this to the
printer.

### Why a guard that already existed did not catch it

`UX-218`'s stated acceptance was "not *a command is shown* but **the
command runs**". Its implementation:

```python
@pytest.mark.parametrize("step_id", [
    "blast-the-top-element", "sweep-the-capacity"])
def test_every_published_argv_is_executable_as_spelled(self, step_id):
```

Two ids, written by hand, against a fixture **outside a store** — so
the two store-shaped steps were neither listed nor offered, and both of
them were broken. The same shape as `UX-325`'s round-12 CI list, in a
test instead of a workflow. The parametrize is now derived from the
fixture's own report, and the store-shaped steps are exercised by
`tests/unit/test_the_printed_sentences_are_contracts.py` against a
fixture that *is* in a store.

### Parsing, not running — and a near-miss worth recording

Two of the four steps cannot be executed by a unit test: `measure-again`
runs a real build, and `compare-with-the-run-before` compares against a
capture that does not exist yet. Both are declared in `UNRUNNABLE` with
a written reason, and a clause keeps exemptions a minority of the steps
offered.

The first draft checked those two by appending `--help` to the argv and
shelling out. **It ran a real build inside a unit test** — `--help`
lands *inside* a REMAINDER positional, so `bga snapshot --project P --
bst build all.bst --help` is a capture with a fourth argument. That is
why `tools/bga_snapshot.py` grew a `create_parser()`: the honest check
is to parse the command with the parser that will receive it.

Parsing alone is not the check either, and the guard says so: `bga
snapshot /abs/path` **parses fine** — REMAINDER swallows anything. What
it parses *into* is the assertion:

```python
assert parsed.project           # not None, or the project is the build
assert command[0] == "bst"      # or `bga snapshot` refuses it
```

### F4, before and after

```text
$ bga compare tests/fixtures/macro_micro/run tests/fixtures/macro_micro/run
  Warning: neither run records which `bga` measured it (both predate the producer stamp), …
before:  (--allow-mismatch was given; treat every figure below with real skepticism)
after:   (a caveat, not a refusal - no flag was needed and the figures below still compare)
```

No flags were passed in either run. The sentence was gated on
`comparability_warning`, which also accumulates the cross-host caveat
(`UX-186`) and the producer note (`UX-249`). The correct condition is
`mismatches`, and it is checkable rather than assumed: `bga compare`
**refuses outright** when `mismatches` is non-empty and the flag was not
given, so a comparison that is being printed with mismatches is one
where it was.

### The sweep the filing asked for

Every sentence in `bga/report/` claiming a flag *was given or passed*,
with what it is gated on:

```text
--allow-mismatch was given            -> comparison.mismatches        (was: comparability_warning)
`--fail-on-low-confidence` was passed -> conditional prose about behaviour, not a claim  (correct)
```

Two, and only one was wrong. Twelve other flag-naming sentences were
read and are *offers* ("try `--capacity N`", "see `--format json`"),
which claim nothing about what was passed. The inventory is held by a
clause, so a third one has to be classified rather than merely written.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| Y1 | `measure-again` publishes `['bga', 'snapshot', project]` again — the exact F3 defect | the parses-into-shape clause |
| Y2 | `compare-with-the-run-before` publishes `--project` again | the every-argv-parses clause |
| Y3 | the `--allow-mismatch` line gated on `comparability_warning` again | the caveat clause |
| Y4 | the caveat branch deleted entirely | the caveat clause — so the fix is a gate, not a deletion. Its first form did not apply cleanly and was rewritten before being counted; a mutation that does not land proves nothing |
| Y5 | `run_instance` stops publishing `targets` | 3: steps-are-offered, parses-into-shape, and the stale-exemption clause — the step disappears rather than being spelled wrong, which is the intended behaviour and is why three clauses see it |

### Deviation from the Required Fix

- The filing said "the second printer retired". There is no second
  printer: `bga/report/text.py` and the JSON report both call
  `compute_next_steps`, and the page renders what the JSON publishes.
  The unguarded second path was in the **test**, not in the code, and
  that is what was retired.
- Three commands were wrong, not one. The third was found by the guard
  on its first run.
- `run_instance` gains `targets` — a published field, which is more than
  "fixes the printer". It is the enabling fact: without it the capture
  step cannot be spelled at all, and the alternative was to keep
  printing something that does not run.
