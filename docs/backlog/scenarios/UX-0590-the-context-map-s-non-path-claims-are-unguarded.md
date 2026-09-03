# UX-590: the context map's non-path claims are unguarded

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-573 (the map that walks the tree git has), UX-274 | **Serves:** every session that reads fixing guide §6 to find where a thing lives | **Topic:** guards

## Motivation

`UX-573` found fixing guide §6 crediting `bga/report/` with a `csv`
renderer it does not have, and dropped the word. Its own Outcome
records why nothing caught it:

```text
UX-0573…md:121   "Dropping `csv` is a doc correction with no guard: the
                  existence direction reads only path-shaped tokens,
                  and a bare `csv` has no path"
```

The guard is `tests/unit/test_the_context_map_is_the_tree.py`. It
holds both directions for anything shaped like a path — every path in
the map exists, every tracked directory reaches the map. A capability
named in prose (`csv`, a flag, a format, a command) is invisible to
it, so §6 can credit the tree with anything that is not spelled with a
slash. That is the class of claim `UX-088` was filed for and the one
`UX-573` found again seventeen rounds later.

## Required Fix

The map's capability nouns derived rather than asserted: a format
named in §6 must appear in the writer's own registry (the
`--format` choices `bga/cli.py` declares), a command named must be a
registered subcommand, and a word in neither is red unless it is on
an explicit prose allowlist with a reason. The `UX-582` shape — the
table is the subject, the guard reads it both ways.

## Out of Scope

- The path directions — they hold and were re-mutated in `UX-573`.
- Prose outside §6 — declined: the map is the claim this item is
  about, and a sweep of every document's capability nouns is a
  different population with a different vacuity floor.

## Acceptance Test

Mutation: re-add `csv` to §6's `bga/report/` row — red naming the
registry it is not in; add a real format to the registry and not to
the map — red the other way.

## Outcome (round 84, 2026-09-03) — 🔴 guard landed, row not moved

**Premise: half falsified.** `csv` *is* in the writer's registry — six
subcommands declare it — so the Acceptance Test's first mutation is
green by design, and correctly:

```text
$ python3 -c "...create_parser(); per-subcommand --format choices"
analyze ['text','json','csv']   diagnostics ['text','json','csv']
floors  ['text','json','csv']   graph       ['text','json','csv']
replay  ['text','json','csv']   utilisation ['text','json','csv']
compare ['text','json','ci-comment']   blast/cache-trend/correlate/sweep/whatif ['text','json']
$ grep -n "format_csv" bga/report/text.py        1090:def format_csv(...)
```

What `UX-573` removed was a bare `csv` sitting in a list of *filenames*
(`text.py, json.py, csv, ci_comment.py`) — a path claim, not a format
claim. The renderer exists; `bga/report/csv.py` does not.

The gap that is real, measured at `8f51a26`:

```text
$ registered commands (13 subcommands + 19 tool aliases)   32
  ... named nowhere in §6                                  15
$ registered --format choices                               4
  ... named nowhere in §6            csv, ci-comment         2
$ grep -rln "fixing-guide" tests/ | xargs grep -l "§6\|section 6"
tests/unit/test_the_context_map_is_the_tree.py    (paths only)
```

**Close.** §6 gains one row — `--format  text, json, csv, ci-comment` —
held to `bga/cli.py` both ways, and the `csv` *shape* gains a scan: a
bare word in one of §6's comma lists of paths must be a registered
command or format, or carry a reason in `PROSE_IN_A_PATH_LIST`.

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_context_map_is_the_tree.py -q
25 passed in 0.59s
$ make test-touching       23 file(s) selected · 579 passed, 3 skipped in 15.43s
$ make lint                All checks passed!
```

**Mutations.**

| mutation | anchor confirmed | red | count |
|---|---|---|---|
| re-add `csv` to `bga/report/`'s row | `json.py, csv, ci_comment.py` | *green* — registered | 25 passed |
| `parquet` where `csv` sat | `json.py, parquet, ci_comment.py` | `…a_bare_word_among_paths…` | 1 failed, 24 passed |
| `+'toml'` to `compare --format` in `bga/cli.py` | `'ci-comment', 'toml'` | `…every_registered_format_is_on_the_map` | 1 failed, 24 passed |
| `parquet` added to the `--format` row | `^--format` line | `…every_format_the_map_names_is_registered` | 1 failed, 24 passed |
| the `--format` row deleted | `grep -c "^--format"` → 0 | four clauses | 4 failed, 21 passed |
| `PATH_SUFFIXES = (".nope",)` | line 177 | `…scan_reads_a_non_empty_population` +3 | 4 failed, 21 passed |
| `set(TOOL_ALIASES)` → `set()` | line 130 | `…registry_is_a_non_empty_population` | 1 failed, 24 passed |
| `whatif` added to the `--format` row | `^--format` line | `…format_row_answers_no_path_question` | 2 failed, 23 passed |

**A guard that did not discriminate as written.** `tables` added to the
`--format` row did *not* red `…format_row_answers_no_path_question`:
viewer basenames keep their suffix (`tables.js`), so only a Python
module basename collides. `whatif` reds it, and that is the clause's
real reach.

**Deviation from the Required Fix.** The command half is direction
(a) only — a command *named* in §6 is checked, but the registry's 32
commands are not held to appear there. Naming them costs ~920 B and
`docs/contributing/fixing-guide.md` is 41,358 B: `round(B/1024)` is
40 with 114 B of headroom, and `UX-584` requires that figure in both
the guide *and* `docs/contributing/rules.md`, which is another track's
file this round. The `--format` row costs 81 B and fits. Filing the
command vocabulary — and the guide/rules KB coupling that blocks any
addition over 114 B — as a follow-on row.
