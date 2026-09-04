# The rules card

Every rule this repository holds a session to, one line each, with the
guard that catches it and the [fixing guide](fixing-guide.md) section
that argues it. **Read the guide's paragraph for the rule you are about
to break, not the whole guide** — it is ~50 KB because every rule carries
the incident that produced it, and the incidents are why the rules are
trusted (`UX-505`).

## Working a task — §2

| rule | guard |
|---|---|
| Read the task file fully, then only the line ranges it cites | — |
| Replace the placeholder; a removed comment is not an implementation | — |
| Stay inside the declared scope; a bug you notice becomes a row | — |
| Touching the page? Run the styleguide's seven questions | `test_the_page_conforms_to_its_sections.py` |
| Never delete, weaken or skip a test to make a change pass | `.claude/hooks/keep-the-guards-able-to-fail.sh` |

## Definition of Done — §3

| rule | guard |
|---|---|
| 🟢 only after *you* ran the Acceptance Test, output pasted | — judgement: nothing can see who ran it |
| Some claims have no local instrument — open the PR first (§7) | — |
| A history figure from a shallow clone is worth nothing — ask `--is-shallow-repository` first | `test_a_guard_that_reads_history_declares_its_depth.py` |
| `make test-touching` while you work; the tier when it is wider | `test_the_loop_stays_fast.py` — the selector, not that you ran it |
| `make test` before anything is marked done. A tier is a selector | — |
| Both status markers, same commit; the counts are derived | `test_docs_links_and_commands.py` |
| A number or mechanism you moved: annotate the file asserting it | `tools/dev_close_task.py --figures`, held by `test_the_loop_stays_fast.py` |
| A renamed or removed published key bumps its schema version | `test_output_schemas.py` |
| A key entering `required` under a live id bumps it too | `test_a_required_set_grew_under_an_unchanged_id.py` |
| Roles served, or how well? `docs/design/roles.md` in the same commit | — judgement: "how well" is not mechanical |
| A guard that asserts an order reads the order, never restates it | `test_the_order_the_page_has.py` — one worked example, not every order guard |
| Architecture or spec made wrong? Same commit | `test_the_documents_keep_up_with_the_contracts.py` |
| Documentation you are not writing now: file the row first | `test_documentation_debt_has_a_door.py` |
| Acceptance test still failing? 🟡 with what is blocking, and stop | — |

## Committing — §4, §4a

| rule | guard |
|---|---|
| One task, one commit | — judgement: a commit's scope is not readable from it |
| **Never `git add -A` or `git add .`** — stage paths by name | `.claude/hooks/no-bulk-add.sh` |
| Read the full staged list before every commit | — |
| `make check-clean` before committing | `make check-clean` |
| Quote version specifiers; check `git status` after any `>` | — judgement: the damage is a stray file, and `make check-clean` sees that |
| Scratch files live outside the repo | `make check-clean` |

## Hard rules — §5

| rule | guard |
|---|---|
| Never mark 🟢 without a pasted, passing command | — judgement: a pasted block cannot be re-run |
| Never leave a no-op placeholder and call it implemented | — |
| Never widen scope | — |
| Never invent data the spec says must be `UNKNOWN` or absent | `test_a_retired_state_is_declared.py` |
| Never touch `docs/spec/specification.md` outside Part 32's registry | `test_the_spec_outside_part_32_is_read_only.py` |
| **Never let an instrument read a proxy for the thing it names** | `test_the_agent_configuration_holds.py` — the `measure` skill states the three questions; asking them is judgement |
| Exact integer arithmetic for anything invariant-related | — |

The proxy rule is the one this repository breaks most — about thirty
sightings across twenty-six items, in four shapes. §5 names all four
with a worked example each; read it before writing a guard.

## Which kind of session is this? — §6a

| stream | starts from | done when |
|---|---|---|
| **design** | a question about where the tool should go | it names who it serves and what it declines |
| **audit** | a landed range, or external feedback | every claim is a pasted measurement |
| **feature** | a 🔴 row whose Depends on is clear | §3, in full |
| **fix** | a defect, from CI or a report | the case that reproduced it is a committed guard |
| **documentation** | a wrong doc, or a §3.11 filing | the guard exists, or its absence is stated |
| **refactor** | a measured cost — size, duplication, a budget | the measurement moved and no behaviour did |
| **review** | the diff since the last architecture-review row | every item answered with a measurement or a filing |
| **release** | a contract that moved | the derivation guard is green |

A stream's output is another stream's input; a session doing two is two
sessions. §3 does not vary by stream.
