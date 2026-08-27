# Architecture and documentation review

A round type, and its log. Feature audits happen here on a cadence —
twenty-eight rounds of them — and documentation review did not, which
is why one drifted a whole axis and the other did not (`UX-241`).

## What a review is

| | |
|---|---|
| **input** | everything that landed since the last row in the log below |
| **output** | filings, in `docs/backlog/scenarios/` — and this document's next row |
| **produces no code** | a review that fixes what it finds is a fix session wearing a review's name, and stops being able to see the next thing |
| **done when** | every item on the checklist has been answered with a measurement or a filing |

The stream table in
[`../contributing/fixing-guide.md`](../contributing/fixing-guide.md)
§6a carries it beside the other six.

## The checklist

Per architecture chapter, per guide:

1. **Does the code still do what it says?** Not "is it plausible" —
   open the module the chapter names and check the mechanism.
2. **Does every published contract have a home?**
   `test_the_documents_keep_up_with_the_contracts.py` guards the
   mechanical half (`UX-233`); the review asks whether the *prose*
   around each one is still true.
3. **Is any figure invalidated?** `git grep` the number. A figure a
   later round moved and an earlier document still quotes is the defect
   `UX-132` named.
4. **What shipped since the last review that no document names?** The
   inventories are `bga --help`, `schemas.names()`, and the closed rows
   added since the last log entry.
5. **Does each document's own "last updated" claim match reality?**
   `git log -1 --date=short -- <file>` against what the file says.

The spec's Part text is out of scope: it is ground truth, and a review
that finds it wrong files against it rather than editing it.

## The cadence, and why it is measured in closed rows

The trigger is a number, not a memory:
`tests/unit/test_the_review_has_a_cadence.py` reddens when more than
**25 scenarios** have closed since the last row below.

Closed rows rather than commits, because a commit is not a unit of
change here — one round is anywhere from one to nine of them — and
because the count is in the tree, so the guard needs no git and gives
the same answer on every machine. 25 is chosen against the drift that
was actually missed: the viewer axis ran from `UX-193` to `UX-226`, 34
closed rows, with nothing in the process to notice. A bound below that
would have caught it; a bound at it would only just have.

## The log

<!-- UX-332: the commit column is gone. It cited the branch commit each
     review ran against, and this repository merges pull requests - so a
     hash that names a branch tip is only as durable as the branch.
     Measured on the four rows it carried: three of the four are **not
     reachable from `origin/main`**, so a reader with an ordinary clone
     cannot resolve them, and the one that is (`b17d741`) is reachable
     by luck of which pull request kept its commits rather than by
     anything the column guaranteed.

     "Closed rows at review" is the merge-stable identity and was
     already here: a count in the tree, what the cadence guard measures
     distance in, and immune to any merge strategy. -->

| review | date | closed rows at review | findings |
|---|---|---|---|
| 1 | 2026-08-23 | 237 | `UX-245`, `UX-246`, `UX-247` |
| 2 | 2026-08-24 | 263 | `UX-273`, `UX-274` |
| 3 | 2026-08-25 | 290 | `UX-294`, `UX-295` |
| 4 | 2026-08-26 | 318 | `UX-322`, `UX-323` |

### Review 3 — 2026-08-25

Twenty-seven rows closed since review 2, which is what tripped the
cadence. Run against `docs/design/architecture.md`, the three guides
and the seven published contracts.

**1. Does the code still do what it says?** The CLI table checked
against `cli.create_parser()`: twelve subcommands, twelve rows, plus
the alias row `UX-67` added — no drift. The viewer section checked
against `bga/viewer/`: the schema-driven claim, the width rule and the
presets are all still what the modules do, and the chapters `UX-286`
added were missing from it and were written in by `UX-247` the same
day.

**2. Does every published contract have a home?**

```text
contract              named in architecture.md   named in a guide
analyze/v2                     4                        2
blast/v1                       1                        1
compare/v1                     1                        1
correlate/v1                   1                        1
store-aggregate/v1             1                        1
store/v1                       1                        1
whatif/v1                      3                        0
```

Six of seven are reachable from a guide. `whatif/v1` is not — the
*command* is documented in two guides and the *contract* in none, so a
consumer holding a payload stamped with it has nowhere to look. Filed
as `UX-295`.

**3. Is any figure invalidated?** One, and it was this round's own:
`UX-285` and `UX-286` recorded their after-measurements against
"macro_micro" when the export measured was the golden
`mixed_task_kinds` fixture. Corrected in place, with a note in `UX-285`
saying so — the two fixtures are different documents and a reader
comparing rounds would have been comparing two runs.

Direction 13's own figures (48 sections, 18.8 and 20.1 screens) are
*not* invalidated: they are dated round-38 measurements and the round
that moved them is named beside them.

**4. What shipped since the last review that no document names?** The
inventories: `bga --help` (twelve subcommands, nineteen aliases),
`schemas.names()` (seven contracts) and the twenty-seven closed rows.
The commands and contracts are covered. The **modules are not** — the
architecture names `app.js` and `chapters.js` and none of the other
ten viewer modules, including the 2,411-line `views.js` that draws
every section. Filed as `UX-294`.

**5. Does each document's "last updated" claim match reality?**
`architecture.md` claims 2026-08-25 and was last changed 2026-08-25.
It is still the only document making the claim, which is what `UX-247`
recorded — and that clause is now guarded rather than checked by hand,
which is why this review could answer it in one command.

**No code was written in this review.** `UX-294` and `UX-295` are the
output, plus this row.

### Review 1 — 2026-08-23

The first one, run against `docs/design/architecture.md` and the three
live guides. Three findings, each measured:

**The architecture's CLI table is two subcommands behind.** Checked
against `cli.create_parser()`:

```text
subcommands in `bga --help`, absent from "## Real current CLI surface":
  blast    (shipped round 19, UX-172)
  whatif   (shipped round 28, UX-230)
```

`--explain` (`UX-229`) appears nowhere in the document either, although
the provenance mechanism it prints is described. Filed as `UX-245`.

**The end-to-end guide never reaches the command for its own last
step.** `docs/guides/real-project.md` walks capture → read → go inside
→ join → act → gate, and `bga whatif` — which prices the act step — is
named nowhere in it. Filed as `UX-246`.

**The architecture's own Verification Log is stale about itself.** It
says *"Updated 2026-08-18 (after `UX-76`)"*; `git log` says the file
was last written on 2026-08-23, with five commits touching it since
that line was written. A log that does not move when the document does
is worse than no log, because it is read as a claim. Filed as `UX-247`.

**What was checked and found current:** every published schema id
appears in spec Part 32.5 and the architecture inventory (guarded since
`UX-233`); the three planes' chapters match the modules they name; the
33% five-capture noise figure and the band derived from it are the ones
the round-9 audit measured; `docs/guides/cli.md` names every subcommand
and every `tools/` alias. `optimization-walkthrough.md` names almost no
command, which is correct — it is a tombstone pointing at
`real-project.md` (`UX-139`), not a guide.

### Review 2 — 2026-08-24

Twenty-six rows closed since review 1 — `UX-248`..`UX-272`, the
contract-versioning round, the first recorded release, and rounds 34-36
of the viewer axis. Run against `docs/design/architecture.md` and
`docs/contributing/fixing-guide.md`. Two findings, and one recurrence.

**The rule that draws every nested value is written in one task file.**
Round 36 replaced 34 `<details>object</details>` cells with a rule that
chooses inline / bounded table / fold by **width, not depth**, and it
now governs every object- or array-valued field in every published
schema. Where a maintainer would find it:

```text
$ git grep -c "width, not depth" -- docs/
docs/backlog/scenarios/UX-0267-...md:1
```

The architecture's viewer chapter describes the *hint* half of
schema-driven rendering in detail — `bga:quantity`, `bga:columns`,
`bga:rail` — and says nothing about what becomes of a field's value, so
a schema author reading the chapter learns that adding a field is free
and does not learn that its shape decides its rendering. Same shape as
`UX-244`. Filed as `UX-273`.

**The context map is guarded on `bga/` and `tools/` and nowhere else.**
`UX-239` regenerated §6 of the fixing guide and gave it a guard;
`_real_modules()` globs two roots, so the **Tests and docs** block has
been unguarded prose ever since, and it has drifted exactly as far as
an unguarded figure does:

```text
map says                                    tree says
tests/unit/  218 files, ~3,100 tests        240 files, 3,327 tests
closed.md    the 233 closed rows            263 closed rows
entries named under tests/:  5              real entries:  12
```

The seven absent entries include both harnesses this axis just built —
`tests/dom_shim.mjs` (`UX-264`) and `tests/cdp.mjs` + `tests/browser.py`
(`UX-257`) — so a session that needs to assert something about the page
is pointed at neither, which is how twenty-five inline shims got
written in the first place. Filed as `UX-274`.

**`UX-247` recurred, wider.** The architecture's Verification Log still
opens *"Updated 2026-08-18 (after `UX-76`)"*; `git log -1 --date=short`
now says `2026-08-24`, with **12** commits touching the file since that
line was written — five at review 1. The finding is unchanged and the
gap grew by six days and seven commits while the item sat open, which
is the argument for its clause 2 (guard the mechanical half) rather
than for re-editing the date by hand a third time.

**Review 1's three findings are all still open** (`UX-245`, `UX-246`,
`UX-247` — all 🔴). A review that files and never closes is a review
that produces a longer list, not a truer document; that is a fact about
this round's ordering rather than a finding, but the next review should
read it as one if it is still true.

**What was checked and found current:** the contracts table names all
nine published schemas and the mechanical half is guarded
(`test_the_documents_keep_up_with_the_contracts.py`, 6 passed); the
`producer` block and the release mechanism (`UX-249`..`UX-252`) reached
`architecture.md`, `docs/guides/cli.md` and
`docs/contributing/release-guide.md`; the viewer chapter's CSP
paragraph is current to `UX-265`, naming the pre-flight, the private-
network header and the style-attribute consequence, which is round 34's
work correctly landed in prose; the `bga/` and `tools/` halves of the
context map pass their guard (7 passed) and gained `contracts.py`,
`producer.py` and `bga_release_notes.py` in the rounds that shipped
them. `UX-245`'s measurement is unchanged — `bga blast` and `bga whatif`
are still the two rows the CLI table lacks, and `--explain` still
appears nowhere — so it needs no re-filing, only doing.

### Review 4 — 2026-08-26

Twenty-eight rows closed since review 3, which is what tripped the
cadence — and it tripped mid-round, on the closure of `UX-315`, which
is the mechanism working: the trigger is a number in the tree rather
than a memory.

**1. Does the code still do what it says?** The CLI table checked
against the parser and against `bga --help`, by running every command
the table names and every command the tool has:

```text
rows in the architecture's table   18   all name a real command
commands that work                 20
missing from the table              2   bga view, bga timeline
```

Filed as `UX-322`. It is a recurrence of `UX-245` — the same table, two
commands behind, three reviews later — and this time the two missing
are `bga view`, the entry point for the whole viewer axis from `UX-193`
to `UX-320`, and `bga timeline`, `UX-298`'s native Perfetto emitter.
Both are named in the document's prose and absent from the list built
to be read as a list. The filing asks for a guard as well as the rows,
because a hand-maintained table against a parser that knows the answer
will drift a fourth time.

**2. Does every published contract have a home?**

```text
contract              architecture   guides
analyze/v2                      4        2
blast/v1                        1        1
compare/v1                      1        1
correlate/v1                    1        1
store-aggregate/v1              1        1
store/v1                        1        1
whatif/v1                       5        1
```

Seven of seven, both columns. Review 3's one finding here — `whatif/v1`
documented as a command and not as a contract — is closed by `UX-295`,
and this is the check confirming it.

**3. Is any figure invalidated?** One, and it is the round-41 claim
this round spent two items on. `docs/audits/round-41.md` line 86 still
states, unqualified, that "175 KB of the 196 KB page is commented
JavaScript, because `--export` inlines modules verbatim". Both halves
are false: `_uncommented` has stripped comments since `UX-205`,
`UX-320` measured the page at 89% code, and `UX-307` this round
removed what was actually left — 153 B. Nothing in the file marks it.
Filed as `UX-323`.

It is not an inert error. It is the stated reason the `UX-287` ratio
threshold went 4x → 3.5x, and the threshold has since moved again to
3.3x — twice restated against a misattributed cause. `architecture.md`
was checked and is **not** affected: it reports the falsification
rather than repeating the claim.

**4. What shipped since the last review that no document names?** The
inventories: `bga --help` (20 commands), `schemas.names()` (7
contracts) and the twenty-eight closed rows. The contracts are
covered; the commands are `UX-322`. The viewer module map, which
review 3 filed as `UX-294`, gained `tablefocus.js` in round 44 and it
was written into the map in the same round — so the guard `UX-294`
produced is holding, which is what a closed finding should look like
one review later.

**5. Does each document's "last updated" claim match reality?**
`architecture.md`'s Verification Log carries a round-44 entry dated
2026-08-26 and the file was last changed 2026-08-26. It remains the
only document making the claim, and `UX-247`'s guard now checks it
rather than a reviewer doing so by hand — this review confirmed the
guard is in the suite and green rather than re-deriving its answer.

**No code was produced by this review**, per the rule above. The two
findings are filings.
