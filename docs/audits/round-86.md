# Round 86 — the boundary of a population, and where guards go quiet

Input: the rows open after [round 85](round-85.md) merged — `UX-628`
and `UX-629` from architecture review 15, `UX-630`, `UX-631` and
`UX-632` filed by round 85 against its own work, and `UX-597`, which
round 85 was told to leave alone and whose block had lifted. Three more
arrived during the round: `UX-633` and `UX-634` from `UX-597`'s
measurement and the repository owner's proposal, and `UX-635` from a
gap `UX-630`'s track measured and did not file.

Round 85's finding was that **a premise carried forward is a sentence
again**. Round 86's is one step to the side of it. Every item here
turned out to be about the same thing, and not one of them was filed as
such:

> a guard's population is bounded by a rule somebody typed, and where
> that rule is wider than the claim, the guard does not fail — it goes
> quiet.

**Six of the eight items are that shape.** In three of them the
narrowing was invisible to every other clause in the same file.

## Decomposition

| track | rows | why together |
|---|---|---|
| I (here) | `UX-597` → `UX-633` → `UX-634` | all three are the release contract; serial on one guard file |
| K | `UX-628` → `UX-629` | both touch `bga/schemas.py` and the contract prose |
| L | `UX-631` → `UX-632` | both touch `docs/contributing/fixing-guide.md` |
| M | `UX-630` | disjoint: a guide section and a new guard |

Merge hotspots (`README.md`, `closed.md`, `tiers.py`) were the
orchestrating session's, once, at the end — as
[`decompose`](../../.claude/skills/decompose/SKILL.md) §3 says.

## The population that was wider than the claim

Six items, one table. The last column is what the over-broad rule hid.

| row | the rule as written | what it excluded, silently |
|---|---|---|
| `UX-628` | the contracts guard's population was contract **ids** | 84 of 199 published keys named in no document; the guard was green throughout |
| `UX-629` | `required` is a validator's population | a `compare/v2` document written a week earlier stopped validating, and the versioning rule called it an addition |
| `UX-631` | `_named` matched a filename against **the whole map** | 21 of 26 package modules were "answered" by another package's row — `bga/report/rate.py` by the word `rate` inside `generated` |
| `UX-632` | `SITES` emptied in a mutation | the parametrized clauses collected nothing and reported as **skips**, not failures |
| `UX-633` | a version floor at `0.3.0` | `v0.2.0`, which passed two of three clauses and failed only reachability — and any future unreachable tag |
| `UX-635` (filed) | the inventory scans the `BGA_*` prefix | 21 `BST_TRACE_*` names in `bwrap_shim.py` that no `BGA_*` guard can see |
| `UX-636` (filed) | the contracts guard's *repaired* population is a frozen register | the 80 keys still in it, which the ratchet bounds but does not pay |

The repair is the same move in each: **name the exclusion, and give the
name a clause of its own.** `UX-633` is the clearest — the floor became
`UNREACHABLE_BY_DECISION = {"v0.2.0"}` plus
`test_each_named_exception_still_needs_naming`, which reddens when a
listed tag stops needing the exemption. `UX-630` reached the same
answer before it had the problem: `BGA_STRICT_HINTS` is a browser
global and `BGA_TIER_ANY` is written and never read, and both are in
the table named for what they are rather than in an exclusion list.

## The round's own instance of it

`UX-597`'s guard skips where a checkout has no tags. `UX-449`'s scan
reads skip reasons **as written**, so an undeclared one is red on every
machine whether or not it fires. I did not see it, because I ran
`make test-touching` — a *selector*, whose population is files naming
the modules the diff touched, and `test_every_skip_reason_is_declared.py`
names none of them. It cost one red CI run on two interpreters.

```text
$ make test          # the gate, run late
6935 passed, 29 skipped in 497.75s
```

That is the second entry in `CLAUDE.md`'s "Things Claude gets wrong",
committed by the session holding the round. It belongs in this document
rather than only in `UX-597`'s file because it is the same defect as
the table above, one level up: **a selector is a population, and a
population is not a gate.**

## What each item left

| row | what shipped | held by |
|---|---|---|
| `UX-597` | five clauses over every release row; `fetch-tags: true` on CI's checkout | `test_a_release_records_a_contract_state.py` |
| `UX-628` | every published key named in the prose; register 84 → 80 | `test_the_documents_keep_up_with_the_contracts.py`, 15 clauses |
| `UX-629` | §3.7's third clause, and `bga:always_written` as the escape it names | `test_a_required_set_grew_under_an_unchanged_id.py`, 14 clauses |
| `UX-630` | the environment table in `docs/guides/cli.md`, scanned against the tree | `test_the_environment_surface_is_an_inventory.py` |
| `UX-631` | the map's rule is per-row, not per-map | `test_the_context_map_is_the_tree.py` |
| `UX-632` | the loop's cost derived by `dev_touching.py --spread`, written by `--write` | `test_the_cost_row_is_derived_from_the_selector.py` |
| `UX-633` | one named exemption instead of a version floor | `test_a_release_records_a_contract_state.py` |
| `UX-634` | step 8 publishes the release; the description is cut, not rewritten | `test_a_release_records_a_contract_state.py` |

`UX-632` is the one to read twice. Wall-clock seconds have no local
instrument (`UX-551`), so the figure three documents quoted was
re-typed each round. It is now derived from the **selection** — a
property of the tree the guard already computes — and its first live
run reddened on the merge, at 462 → 463 test files, and again at 464.
That is the loop working on its first day.

## Deviations worth carrying forward

- `UX-633`'s **Acceptance Test as filed** presumed the `v0.2.0` tag
  would be deleted. The repository's owner decided it stays, so the
  clause that shipped is the same shape with the sign flipped. Written
  down rather than quietly re-scoped: the two read alike in a diff.
- `UX-632` could not put its figure in `CLAUDE.md` — `UX-471`'s guard
  forbids that file a count the tree moves under it. `CLAUDE.md` now
  prices the loop in nothing and defers to the guide. Three sites
  corrected, two carrying the figure.
- `UX-629` states its own cost: `required` was a guarantee a
  *validator* enforced and the replacement is one a *guard* enforces,
  which a consumer cannot check from the document alone. That is the
  price of not breaking what they already wrote.
- **Four guards written this round did not discriminate on their first
  run** and are recorded in their task files — two in `UX-628`, one in
  `UX-631`, one in `UX-632`. `UX-631`'s is the instructive one: the
  negative examples were saved by a `.py` suffix rather than by the
  scoping the clause was about, so the scoping was untested.
- One mutation (`UX-634`'s N4) came back **green because the `sed` did
  not apply**, and reddened on re-run. A mutation that appears not to
  land is two hypotheses, not one.

## The count

Eight rows closed, four filed (`UX-633`, `UX-634`, `UX-635`,
`UX-636`), 634 in the backlog. Direction 10 — releases as contract states — is `landed`:
the tags exist, a guard reads them, and step 8 publishes.
