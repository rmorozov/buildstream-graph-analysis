# UX-653: a contract bump rewrites the record of what it superseded

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-247 (which built the log this rewrites) | **Found by:** architecture review 16 | **Serves:** anyone reading the verification log to find out what was checked, and when | **Topic:** docs

## Motivation

`architecture.md`'s Verification Log is a stack of dated records: each
says what was re-grounded on that date and against what. A record is
worth having only if it says what was true then. Everything below is
measured at `a5030a4`, the state this review found; the restoration it
describes is in review 16's own commit. The 2026-08-25 entry said:

> Updated 2026-08-25 (after `UX-286`) … the contracts table's
> `analyze/v6` row is checked against the keys the schema declares

`analyze/v6` did not exist on 2026-08-25. It was published on
2026-09-04, ten days later.

```console
$ python3 - <<'PY'
import re, pathlib, subprocess
DOC = "docs/design/architecture.md"
log = pathlib.Path(DOC).read_text(encoding="utf-8").split(
    "## Verification Log", 1)[1]
for entry in re.split(
        r"(?=^Updated \d{4}-\d{2}-\d{2} \(after `UX-\d+`\))", log, flags=re.M):
    head = re.match(r"^Updated (\d{4}-\d{2}-\d{2}) \(after `(UX-\d+)`\)", entry)
    ids = sorted(set(re.findall(r"analyze/v\d+", entry or "")))
    if not head or not ids:
        continue
    sha = subprocess.run(["git", "log", "--format=%H", "-1",
                          f"--until={head.group(1)} 23:59:59", "--", DOC],
                         capture_output=True, text=True).stdout.strip()
    body = subprocess.run(["git", "show", f"{sha}:{DOC}"],
                          capture_output=True, text=True).stdout
    live = re.findall(r"^\| `(analyze/v\d+)` \|", body, re.M)[:1]
    print(f"{head.group(1)} {head.group(2):8s} names {ids}; "
          f"table then carried {live}")
PY
2026-09-04 UX-629   names ['analyze/v5']; table then carried ['analyze/v6']
2026-09-04 UX-628   names ['analyze/v5']; table then carried ['analyze/v6']
2026-09-04 UX-622   names ['analyze/v5']; table then carried ['analyze/v6']
2026-09-03 UX-569   names ['analyze/v5']; table then carried ['analyze/v5']
2026-09-03 UX-549   names ['analyze/v5']; table then carried ['analyze/v5']
2026-09-02 UX-535   names ['analyze/v4']; table then carried ['analyze/v5']
2026-08-25 UX-286   names ['analyze/v6']; table then carried ['analyze/v2']
```

(The four rows whose entry and table disagree by one version are the
instrument's own limit, not a finding: each entry was written before
that day's bump, and `--until=<date>` cannot separate the two. That is
`UX-652`, and it is the same day resolution.)

The last row is the finding, and it is not one accident. The sentence
was written as `analyze/v2` and has been carried forward by every
contract bump since:

```console
$ git log --reverse --date=short --format='%ad %h %s' \
      -G "the contracts table's .analyze/v" -- docs/design/architecture.md
2026-08-25 bbbda55 UX-247: the verification log says what is true, and a guard holds it
2026-08-28 12bdecd UX-341: one unit per dimension, and the contract version that says so
2026-08-28 f859e6f UX-344: analyze/v4 - the two namespaces lifted, provenance published once
2026-09-02 fab3307 fix(UX-535): the graph's shape is published once, analyze/v5
2026-09-04 6235fc9 UX-641: a level names its members, not the row number
```

The first commit wrote it, saying `analyze/v2`. The four after it are
every `analyze` bump since, and each one carried the sentence forward:
`v2` → `v3` → `v4` → `v5` → `v6`. Each was a
`git grep`-and-replace of a live id doing exactly what it should
everywhere else in the document, and reaching one place it must not:
the block whose whole purpose is to say what an earlier session
checked.

And it is not carelessness. Restoring the record reddens a guard:

```console
$ python3 -m pytest tests/unit/test_no_document_serves_a_retired_contract.py -q
E   AssertionError: a document a reader reads for what bga does today names a
E   contract nothing writes, without saying so:
E       docs/design/architecture.md:1606  analyze/v2
E           the contracts table's `analyze/v2` row is checked against the keys the
```

`UX-353` requires every retired id in a live document to sit in a
paragraph that says it is retired, and the marker set is
`("never written", "only ever *read*", "superseded")`. A dated log
entry that names the id that was live when it was written therefore
turns red on the day that id retires, and the cheapest green is to
sweep the id forward. Four bumps, four sweeps: the guard asked for
exactly this. Review 16 restored the record by adding the word
*superseded* to the sentence, which is the other green and the one a
reader wants.

Fixing guide item 6 already states the opposite convention for task
files — *"the old figure stays, with one line naming what changed
it"* — because *"a wrong explanation that was believed for a while is
worth being able to recognise again"* (`UX-118`). The Verification Log
is the same shape and has no such rule, and has a guard pushing the
other way.

## Required Fix

Two halves, because one alone would fight `UX-353`.

The Verification Log is stated to be append-only below its newest
entry, in the document and in the fixing guide beside item 6, and a
guard holds it: a commit that changes a *contract id* inside an entry
older than the newest one reddens, naming the entry's date. An
intentional correction to an old record is then an argued exception
rather than the default outcome of a rename. The comparison is over the
entries' text, so it needs no fixture — `git show <parent>:<doc>` gives
the previous body and the entries split on their own headings, as
`test_the_verification_log_is_true.py::_claimed` already does.

And the escape `UX-353` leaves has to be the one a session reaches for
first. Today the marker set is satisfied by the word *superseded*
anywhere in the paragraph, which is a green a rewrite also reaches; the
guide's paragraph beside item 6 says which of the two greens is meant,
so the next bump adds a word rather than a version.

## Out of Scope

- The newest entry. Declined because every round that re-grounds the
  document rewrites it, so a rule that froze it would forbid the log's
  one working mechanism.
- The date comparison itself — `UX-652`.
- The other documents carrying dated blocks
  (`test_a_pasted_guide_block_is_fresh_or_dated.py` holds those, and
  holds them by diffing the block against the command that made it).

## Acceptance Test

Applying `UX-641`'s sweep to the 2026-08-25 entry again reddens the new
guard naming that entry; the same sweep over the newest entry and over
the contract tables above the log stays green.
