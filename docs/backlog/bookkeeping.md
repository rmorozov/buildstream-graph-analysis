# Bookkeeping ledger

One line per bookkeeping finding - a stale figure, a doc naming a
retired flag - never a task file (`UX-998`). `tools/dev_bookkeeping.py`
is the only writer: `--add` appends, `--sweep` lists the open lines
oldest first with the sweeps each survived, `--mark` resolves one.
`merge=union` in `.gitattributes` lets parallel filers append without
colliding.

Format:

    - r<filed> · <status> · <class> · `<path>[:<line>]` · <what drifted> · `<command>`

`status` is `open`, `swept r<N> UX-<id>`, `promoted r<N> UX-<id>`, or
`dropped r<N> <reason>`. `class` is `[a-z][a-z0-9-]*`; a new one needs
`--new-class`. No line stays open past three sweeps - `--sweep`
promotes it to a row or drops it with a reason. The key that catches a
duplicate finding is derived, never written:
`sha1("<path> · <what>")[:7]`.

## Findings

- r140 · open · brief · `.claude/skills/decompose/SKILL.md` · an agent worktree starts at origin/main; the brief must ff-merge the session's commit first, and the skill does not say so · `git -C .claude/worktrees/<agent> log --oneline -1`
- r140 · open · brief · `.claude/agents/verifier.md` · the verifier never runs dev_sizes.py --check, so a hand-typed size row passed it once and was held once this round · `python3 tools/dev_sizes.py --check`
- r140 · open · brief · `.claude/agents/implementer.md` · when dev_touching.py selects the whole suite the brief allows a hand-picked subset; two tracks missed three regressions that way · `python3 tools/dev_touching.py --base <sha> --loud`
- r140 · open · fail-open · `.claude/hooks/selector_before_commit.py:37` · repo_root has UX-992's shape: a payload cwd outside any repo falls back to the main checkout and can fail open · `grep -n 'def repo_root' -A12 .claude/hooks/selector_before_commit.py`
- r140 · open · coverage · `tools/dev_area_pages.py` · 245 of 366 covered rows are inferred from Outcome prose; a row should declare its guard in one field, backfilled from the inferred column · `python3 tools/dev_area_pages.py --areas`
- r140 · open · brief · `tools/dev_touching.py` · hardcodes -n auto; -n 2 works only because trailing args pass through, which nothing documents · `grep -n 'auto' tools/dev_touching.py`
- r140 · open · doc-drift · `.claude/skills/retro/SKILL.md:7` · cites fixing-guide.md §2 for "a drift you notice is a line"; that phrase is rules.md's row, and fixing-guide's own rule is §2.5 · `grep -n "a drift you notice is a line" docs/contributing/fixing-guide.md docs/contributing/rules.md`
- r142 · swept r142 UX-1020 · coverage · `docs/design/rendered-strings.json` · UX-1020's inventory reads golden and macro_micro only; the 1,202-element run and the served Perfetto and SQL pages its Required Fix names are not in it · `grep -n "for label in" tools/dev_rendered_strings.py`
- r142 · open · coverage · `docs/audits/round-142.md` · a round document's and agent-runs.md's commit citations are read against HEAD's ancestry by no guard; 41ded5ef, rebased to 12afba7a, reached both unreachable · `git merge-base --is-ancestor 41ded5ef HEAD`
- r142 · open · coverage · `docs/design/directions.md` · a round-table row's verifier clause is read against its round document by no guard; round 142's row said no verifier ran after seven had · `grep -n "Seven verifiers" docs/audits/round-142.md`
- r143 · open · coverage · `tests/unit/test_the_tiers_are_a_partition.py` · BOOTS_A_BROWSER is matched against _code(), which spaces tokens, so 'from tests.browser import' and 'find_chrome(' never match; only 'from browser import' files are seen · `grep -n 'BOOTS_A_BROWSER' tests/unit/test_the_tiers_are_a_partition.py`
- r143 · open · coverage · `tests/unit/test_the_accent_does_only_its_listed_jobs.py` · a hard-coded hex equal to an accent (.path-box{border:1px solid #8ab4f8}) passes both halves: the guard reads accents by token, not by value · `grep -n 'accent' tests/unit/test_the_accent_does_only_its_listed_jobs.py | head`
- r143 · open · coverage · `tests/unit/test_every_control_has_a_resting_appearance.py` · LOOKS lifts aria-current only, while §6d names aria-pressed and aria-expanded states too; and LOOKS reads no font-weight, so a grade can drift there unseen · `grep -n 'aria-current' tests/unit/test_every_control_has_a_resting_appearance.py`
- r143 · open · coverage · `bga/viewer/style.css` · the UX-1051 form-control base rule widened to 'select, input' reddens nothing: the guard reads only select/text/search and no guard reads a checkbox's look · `grep -n 'input\[type="text"\]' bga/viewer/style.css`
