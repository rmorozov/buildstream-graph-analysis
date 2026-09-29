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

- r140 · dropped r149 already fixed at decompose/SKILL.md:200-205 · brief · `.claude/skills/decompose/SKILL.md` · an agent worktree starts at origin/main; the brief must ff-merge the session's commit first, and the skill does not say so · `git -C .claude/worktrees/<agent> log --oneline -1`
- r140 · swept r149 UX-998 · brief · `.claude/agents/verifier.md` · the verifier never runs dev_sizes.py --check, so a hand-typed size row passed it once and was held once this round · `python3 tools/dev_sizes.py --check`
- r140 · swept r149 UX-998 · brief · `.claude/agents/implementer.md` · when dev_touching.py selects the whole suite the brief allows a hand-picked subset; two tracks missed three regressions that way · `python3 tools/dev_touching.py --base <sha> --loud`
- r140 · swept r149 UX-1041 · fail-open · `.claude/hooks/selector_before_commit.py:37` · repo_root has UX-992's shape: a payload cwd outside any repo falls back to the main checkout and can fail open · `grep -n 'def repo_root' -A12 .claude/hooks/selector_before_commit.py`
- r140 · promoted r149 UX-1092 · coverage · `tools/dev_area_pages.py` · 245 of 366 covered rows are inferred from Outcome prose; a row should declare its guard in one field, backfilled from the inferred column · `python3 tools/dev_area_pages.py --areas`
- r140 · swept r149 UX-998 · brief · `tools/dev_touching.py` · hardcodes -n auto; -n 2 works only because trailing args pass through, which nothing documents · `grep -n 'auto' tools/dev_touching.py`
- r140 · swept r149 UX-998 · doc-drift · `.claude/skills/retro/SKILL.md:7` · cites fixing-guide.md §2 for "a drift you notice is a line"; that phrase is rules.md's row, and fixing-guide's own rule is §2.5 · `grep -n "a drift you notice is a line" docs/contributing/fixing-guide.md docs/contributing/rules.md`
- r142 · swept r142 UX-1020 · coverage · `docs/design/rendered-strings.json` · UX-1020's inventory reads golden and macro_micro only; the 1,202-element run and the served Perfetto and SQL pages its Required Fix names are not in it · `grep -n "for label in" tools/dev_rendered_strings.py`
- r142 · swept r149 UX-998 · coverage · `docs/audits/round-142.md` · a round document's and agent-runs.md's commit citations are read against HEAD's ancestry by no guard; 41ded5ef, rebased to 12afba7a, reached both unreachable · `git merge-base --is-ancestor 41ded5ef HEAD`
- r142 · swept r149 UX-998 · coverage · `docs/design/directions.md` · a round-table row's verifier clause is read against its round document by no guard; round 142's row said no verifier ran after seven had · `grep -n "Seven verifiers" docs/audits/round-142.md`
- r143 · swept r149 UX-998 · coverage · `tests/unit/test_the_tiers_are_a_partition.py` · BOOTS_A_BROWSER is matched against _code(), which spaces tokens, so 'from tests.browser import' and 'find_chrome(' never match; only 'from browser import' files are seen · `grep -n 'BOOTS_A_BROWSER' tests/unit/test_the_tiers_are_a_partition.py`
- r143 · swept r149 UX-998 · coverage · `tests/unit/test_the_accent_does_only_its_listed_jobs.py` · a hard-coded hex equal to an accent (.path-box{border:1px solid #8ab4f8}) passes both halves: the guard reads accents by token, not by value · `grep -n 'accent' tests/unit/test_the_accent_does_only_its_listed_jobs.py | head`
- r143 · swept r149 UX-998 · coverage · `tests/unit/test_every_control_has_a_resting_appearance.py` · LOOKS lifts aria-current only, while §6d names aria-pressed and aria-expanded states too; and LOOKS reads no font-weight, so a grade can drift there unseen · `grep -n 'aria-current' tests/unit/test_every_control_has_a_resting_appearance.py`
- r143 · swept r149 UX-998 · coverage · `bga/viewer/style.css` · the UX-1051 form-control base rule widened to 'select, input' reddens nothing: the guard reads only select/text/search and no guard reads a checkbox's look · `grep -n 'input\[type="text"\]' bga/viewer/style.css`
- r143 · dropped r149 a reading, not a drift; 129px headroom is within the 7,600 bound · coverage · `docs/audits/round-143.md` · macro_micro Perfetto top landed 7,471 px against the 7,600 bound after merge: 129 px of headroom, not the full step the convention derives · `grep -n 'macro_micro' docs/audits/round-143.md`
- r149 · swept r149 UX-998 · doc-drift · `.claude/skills/retro/SKILL.md` · the skill never names the docs/README.md audit-table row a retro report needs, so the first retro found it by a red test_every_named_audit_document_has_a_readme_table_row · `grep -n 'README' .claude/skills/retro/SKILL.md`
- r149 · open · coverage · `.gitattributes` · merge=union on bookkeeping.md keeps both the open and the swept copy of a line two branches marked differently, so a merge silently reopens swept lines; round 149 reopened 12 across two merges · `git log --merges -p -- docs/backlog/bookkeeping.md | grep -c '^+- r'`
- r149 · swept r152 UX-998 · brief · `.claude/skills/verify/SKILL.md` · tells a track to run make test-touching, which UX-1041's hook now refuses in a linked worktree; tracks select with dev_touching.py --list · `grep -n 'test-touching' .claude/skills/verify/SKILL.md`
- r149 · dropped r152 the reading is a free-text attestation used twice; a host registry costs more than it catches · coverage · `tools/dev_close_task.py` · reading_problems checks owner: and unpayable: only for non-empty text, so owner:Narnia passes as readily as a real host · `grep -n 'unpayable' tools/dev_close_task.py`
- r149 · open · coverage · `tests/unit/test_every_control_has_a_resting_appearance.py` · the weight half reads a weight equal to the parent's as inherited, so an explicit font-weight:600 grade under a 600 ancestor passes; and the quiet grade draws at 400 and at 700 (collapse, json-toggle, chapter-open inherit h2/h3) with no rule saying which is meant · `grep -n 'font-weight' tests/unit/test_every_control_has_a_resting_appearance.py`
- r149 · open · coverage · `docs/README.md:97` · says "The other ten each have a command that prints"; 9 do - test_a_counted_figure_is_derived.py holds it to contracts.printable() (schemas.names(), tail/v1 included) while the same block says "the last seventeen" by FILE_WRITTEN, also with tail/v1: 17 + 10 over 26 rows; printable()'s docstring "the subset bga --schema can print" is false for tail/v1 · `python3 -c "from bga.cli import _SCHEMA_BY_COMMAND as C,_SCHEMA_BY_FLAG as F; p=set(C.values()); [p.update(n for _,n in v) for v in F.values()]; print(len(p))"`
- r149 · swept r152 UX-998 · coverage · `tools/dev_process_bands.py:186` · _number() multiplies every tokens cell by 1000, and 24 agent-runs.md rows of rounds 145-148 carry raw counts (88216, not 88k): integrator/sonnet reads a 84154k median and mechanical 261k against 193k rescaled; no guard reads the column's unit · `python3 tools/dev_process_bands.py --runs 400 | grep -E "integrator|^mechanical"`
- r149 · swept r152 UX-998 · coverage · `docs/design/directions.md:2101` · round 148's row says "no separate verifier ran" and omits UX-1105; round-148.md:37 says a verifier ran and found the -j=N leak, agent-runs.md has its row, and round-148.md:48 contradicts :37 - the r142 line was swept by directions.md:1989's prose rule, which no guard reads · `grep -n "verifier" docs/audits/round-148.md`
- r149 · swept r152 UX-998 · doc-drift · `docs/design/anonymized-bundle.md:21` · says CAPTURE_LAYOUT is "13 rows under one snapshot"; bundle._layout_relative() gives 15 - review 29 named it at 14 and filed nothing, and UX-1103 added tail.json's row to the same document's table without the count · `python3 -c "from bga import bundle; print(len(bundle._layout_relative()))"`
- r149 · swept r152 UX-998 · doc-drift · `CLAUDE.md:30` · cites "81 of 189 runs" and bounded's 246k from dev_process_bands.py --runs, which exits 2 as written (--runs takes N); any N gives 83 of 227 and 249k one round later, and the figure carries no date · `python3 tools/dev_process_bands.py --runs 200 | grep -E "^bounded|^judgement"`
- r152 · open · coverage · `tools/dev_baseline.py` · --write --force --reason signs every new finding with one reason, so a merged round's findings are misattributed unless relabelled by hand · `python3 tools/dev_baseline.py --help`
- r152 · open · doc-drift · `.claude/skills/decompose/SKILL.md:167` · the per-item inner loop says make test-touching; a track in a worktree is refused it by the hook (UX-1041), and verify/SKILL.md:24 and implementer.md:194 now say dev_touching.py --base <sha> --list; :41 has the same command · `grep -n 'make test-touching' .claude/skills/decompose/SKILL.md .claude/skills/verify/SKILL.md .claude/agents/implementer.md`
- r152 · open · doc-drift · `docs/design/anonymized-bundle.md:62` · class H says time is shifted to epoch 0, every delta exact; the three raw logs UX-1066 tokenizes carry ts=, wall= and the wrapper stamp verbatim, a deviation its Outcome names and no document does · `grep -n 'verbatim' docs/backlog/scenarios/UX-1066-raw-logs-travel-tokenized.md`
- r152 · open · doc-drift · `docs/design/anonymized-bundle.md:233` · stage 8 Tokenized raw logs is listed as still to do; UX-1066 shipped it in round 152, and line 60 already says tokenized line by line · `grep -n 'Tokenized raw logs' docs/design/anonymized-bundle.md; ls docs/backlog/scenarios/closed | grep 1066`
