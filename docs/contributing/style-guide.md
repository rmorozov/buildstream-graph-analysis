# Documentation style guide

This repository's documentation carries an unusual amount of evidence:
real command output, measured numbers, and the reasoning behind
decisions that are not obvious. That is deliberate and worth keeping.
What it costs is a tendency to accrete — a document grows a section per
round until it is a changelog wearing a design doc's title, and a reader
who needs one fact has to read ten rounds of history to be sure the fact
is current.

These rules exist to keep the evidence and lose the accretion. They are
not style preferences; each one is here because its absence caused a
real problem, named below.

Two of them are enforced by
[`tests/unit/test_docs_links_and_commands.py`](../../tests/unit/test_docs_links_and_commands.py).
The rest are read by people.

**Scope, and its sibling** (`UX-306`). This guide governs the
**documents**. The **web report** has its own contract —
[`docs/design/styleguide.md`](../design/styleguide.md), round 41 —
which governs what a published value renders as, what may be
coloured, what earns emphasis, and what a drawing owes its reader.
The two do not overlap: nothing here decides a pixel, and nothing
there decides a paragraph. If you are changing `bga/viewer/`, that
is the guide you want, and the fixing guide's §2 item 6 is the
checklist.

---

## 1. One document, one job

Every file answers a single question for a single reader. If you cannot
finish the sentence *"this document tells &lt;who&gt; how to &lt;what&gt;"*,
it is two documents.

The folder says which job:

| folder | question it answers | reader |
|---|---|---|
| `docs/spec/` | what must be true | someone implementing or verifying |
| `docs/guides/` | how do I do this | someone using the tool |
| `docs/design/` | why is it this way | someone changing the design |
| `docs/contributing/` | how do I work on this repo | someone editing it |
| `docs/audits/` | what did we find, and when | someone checking history |
| `docs/backlog/` | what is still open | someone picking up work |

**Why:** `design-directions.md` reached 1237 lines by growing a "What
the Nth round found" section per audit. Rounds 7-10 were separate files
the whole time; 2-6 were trapped inside a document whose stated purpose
was "an argument about direction, not a task list". Round 11 split them
out — the design argument is 385 lines and the rounds are where the
other rounds already were.

## 2. Findings are history; documents are current

A guide, a spec or an architecture doc states **what is true now**. When
something changes, edit the statement — do not append a correction
below the old one.

Findings, measurements and decisions-with-dates belong in `docs/audits/`
or in the backlog item that produced them. Those are append-only by
nature; a reader arrives at them expecting a timeline.

**Why:** a document that appends leaves the reader to work out which
paragraph won.

## 3. Say what a command actually is

Instructional documents use the installed entry point:

```bash
bga gen-synthetic /tmp/scale --seed 1     # yes
python3 -m tools.gen_synthetic_scale_run  # no, in a guide   (docs-style: allow-direct-module)
```

`python3 -m tools.<module>` works only from a source checkout with the  <!-- docs-style: allow-direct-module -->
repository root on `sys.path`. A user who installed the package as the
README told them to gets `ModuleNotFoundError`.

The direct-module form is documented **once**, in
[`docs/guides/cli.md`](../guides/cli.md), as a supported alternative for
scripts that want the underlying program. That single mention carries a
`docs-style: allow-direct-module` marker; everywhere else in an
instructional document is a test failure.

Records of what a past round ran — audits, backlog items — are exempt.
Rewriting history to match current style would make it false.

**Why:** `UX-77` found that `bga capture --help` died with a raw
`ModuleNotFoundError` for anyone who installed the package, because
`pyproject.toml` shipped `bga*` and not `tools*`. The aliases and a CI
job that proves all sixteen run from a clean install were the fix. The
README then kept telling people to run the module directly — the same
failure, in the document meant to prevent it. **Enforced by test.**

## 4. Every number is a measurement, and says where from

Quote real output. Name the fixture, capture or command that produced
it. A number with no provenance cannot be re-checked, and this project
has repeatedly found that re-checking is where the bugs are.

```text
3614.2s, 3434.4s, 3405.8s, 3261.2s, 2712.4s — five captures of the same
freedesktop-sdk commit, taken by the scheduled capture workflow
```

is useful. "roughly 5% run-to-run noise" is not, because nobody can tell
later whether it is still true. This example earns its place twice over:
the same list at n=3 supported a 5.8% figure that four docs quoted, and
two more captures took it to 33%. The quoted runs are what made that
re-checkable; a rounded adjective would not have been.

**Why:** `UX-88` found ten documented claims that were checkably false,
including an Efficiency Score formula (`LB / total duration`) that the
code had never implemented (`LB / horizon` — 1.00 vs 0.875 on the golden
fixture). Every one was caught by running the command the doc quoted.

## 5. Links are relative and they resolve

Link to files with repository-relative paths. Do not paste a line number
or an unanchored "see the section below".

**Why:** the docs tree was reorganised in round 11 and 64 links moved
with it. **Enforced by test** — a dangling link fails the suite.

## 6. Lead with the answer

First paragraph: what this is and what the reader gets. Background,
history and justification come after. A reader who needs one fact should
find it without reading the argument for it.

## 7. Prefer a table to a list of near-identical paragraphs

If three consecutive paragraphs differ only in their nouns and numbers,
they are a table. This is the same judgement `UX-89` applied to the
report itself: seven near-identical blocks became one block with ranges,
48 lines became 21, and nothing was lost.

## 8. Markdown must be well-formed, and a linter says so

Write markdown a strict renderer agrees with — most concretely: **every
table row has the same cell count as its header, and a literal `|`
inside a table cell is escaped as `\|`** (GitHub splits rows on pipes
even inside backtick spans). Fenced code blocks are closed, and heading
levels do not skip.

This rule is **enforced**, and by two things rather than one, because
no single tool covers it:

- `make lint-docs` (PyMarkdown, in the `[dev]` extra, part of
  `make lint`) covers the correctness class — fence closure, fenced
  blocks with a language, heading-level jumps, blockquote and list
  spacing. Pure style rules are disabled with a one-line reason each in
  `.pymarkdown.json`.
- **Table cell counts are checked by test**, not by the linter.
  PyMarkdown implements MD001–MD048; the table rules (MD055 pipe style,
  MD056 column count) are markdownlint v0.34+ additions with no
  PyMarkdown equivalent — measured against the real defects, not
  assumed. `tests/unit/test_docs_links_and_commands.py` owns it, which
  is fitting: it is the one markdown defect this repository has
  actually shipped.

**Why:** the round-11 status table rendered broken on GitHub because
one row's summary quoted a jq pipeline — two unescaped pipes turned a
6-column row into 8 cells. A sweep then found four more malformed rows
across three files, one of them broken since the P-task era. Prose
rules cannot catch this class; a linter can, which is `UX-98`.

## 9. Backlog filenames are zero-padded; identifiers are not

A scenario file is `UX-0097-short-slug.md`. The identifier it carries is
`UX-97`.

Those are deliberately different. Lexicographic sort is what every
directory listing, file picker and `git status` uses, and it puts
`UX-100` between `UX-10` and `UX-11` — with 103 scenarios that makes the
listing unreadable. Four digits fix it with room to spare. The
*identifier* stays unpadded because it is what people say, write in
commit messages, and have already written in every audit; padding it
would invalidate all of that to fix a problem the filename already
solved.

**Enforced by test.**

## 10. A direction or a filing says whose problem it solves

Every `## Direction N` section carries a `**Serves:**` line under its
heading, and every backlog filing from `UX-227` on carries `Serves:` in
its header line, both naming role ids from
[the role model](../design/roles.md).

`Serves:` R2, R3 — the two roles a repository-shaped change is usually
about — is a sentence, not a taxonomy exercise: name the roles and say
in a clause why, the way Direction 8 does.

Round 27 wrote the role model and found the reason for this rule: eight
roles, four served thoroughly, four barely — and the imbalance was
invisible for twenty-six rounds because nothing ever required a
document to say who it was for. A gap analysis that has to be
re-derived by reading every filing is one nobody re-derives.

`UX-1`..`UX-226` are deliberately **not** retro-tagged. The archaeology
would be guesswork and a guessed role id is worse than an absent one;
the round history already tells that story.

## 11. The backlog is split by liveness, and a row is an index entry

`docs/backlog/scenarios/README.md` holds the **open** rows;
[`closed.md`](../backlog/scenarios/closed.md) holds the closed ones,
verbatim. A row moves in the same commit that flips its marker, and
`UX ids are never renumbered` — they are load-bearing in task files,
commit messages and guards.

An open row is an *index entry*: id, linked title, topic, priority,
`Serves:`, status. Its narrative lives in the task file, which is the
only place it ever lived twice. Closed rows keep the full narrative
they were written with — history is preserved, not rewritten.

The topic is one word from a closed set — `capture`, `analysis`,
`contracts`, `viewer`, `cli`, `store`, `docs`, `guards` — assigned
mechanically from the task's subject. Where the mechanical answer is
wrong, the task file settles it with a `**Topic:**` field in its header
line, not the row.

Measured before the split: 936 lines, 234 rows, 848 characters per row
on average, and nine of them open.

## 12. Every `Out of Scope` entry names a task or states a decline

An idea parked in an `Out of Scope` section has been lost and dug out
again at least once. Each entry either references a task id — existing
or newly stubbed — or says in a clause why it is declined. A guard
holds this for filings from `UX-227` on.

## 13. Do not restate the code

Explain what is *not* deducible from reading the source: why a threshold
has the value it does, what was measured, what was rejected and why.
Never document a function's parameter list in prose — it goes stale on
the first refactor and the signature is right there.

**Why:** this repository's own comment style already follows this rule;
the docs should not diverge from it.

## 14. A correction bigger than a sentence is a filing

Rule 2 says a document states what is true now, and that when something
changes you edit the statement. That is right when the correction is a
sentence. When it is not — the document describes a mechanism the code
no longer has, or describes nothing where the code grew a whole axis —
the honest move is a backlog row, because the alternative is a session
that started as "fix one line" quietly turning into a rewrite nobody
reviewed.

The counterpart, from the writing side, is item 11 of the
[fixing guide](fixing-guide.md)'s Definition of Done: **documentation a
change needs and does not get is filed before the commit lands.** Not
filing it is not neutral — it moves the cost from the session that
created the debt to the one that trips over it, which is the same
asymmetry rule 2 exists to prevent.

Either way the id is what makes it a decision rather than a shrug. A
filing that says "documented later" and names no id has parked the idea
exactly where `§12` says ideas get lost. **Enforced by test** for the
mechanical half.

**Why:** round 28 shipped three mechanisms whose only documentation was
a docstring or a payload note — `capacity_recommendation`,
`memory_envelope`, and `whatif`'s summing convention. Each survived
because one person said so out loud in a review, which is not a
process. `UX-237` filed the rule; `UX-242`..`UX-244` filed the three.

---

## Editing checklist

- [ ] Does this file still answer one question for one reader?
- [ ] Am I appending where I should be editing? (rule 2)
- [ ] Do the commands use `bga <alias>`? (rule 3, tested)
- [ ] Does every number say where it came from? (rule 4)
- [ ] Do the links resolve? (rule 5, tested — just run `make test`)
- [ ] Would a stranger get the answer from the first paragraph? (rule 6)
- [ ] New backlog file zero-padded to four digits? (rule 9, tested)
- [ ] Do tables render? Same cell count per row, `\|` for literal pipes
      (rule 8 — `make lint-docs`, plus the table test)
- [ ] Did this change need documentation I am not writing? Filed, with an
      id? (rule 14, tested)
