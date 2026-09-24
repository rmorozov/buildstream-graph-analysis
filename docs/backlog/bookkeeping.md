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
