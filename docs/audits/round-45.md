# Audit round 45: the guides, walked by a stranger

Run on 2026-08-27. Two inputs: the sibling's landing of the
round-44 readability slate (UX-316..321, plus UX-307/313/315, the
self-filed UX-322/323, and its fourth standing review), and the
user's proposal that sets the round's method — follow the guides
and READMEs literally, as a new user would, through the
`bga snapshot` → `bga view` workflow across all three planes, and
file every friction worth fixing.

The method note, for the record: the walk was performed under a
stranger protocol — an agent forbidden to read source code or run
the dev suite, allowed only what the documents say and what the
tool prints, on a machine with `bwrap` but no `bst` (a legitimate
newcomer machine), installing from the checkout as the README
says. Every friction was recorded with the exact command, the
exact output, and what a stranger would conclude.

## The landing, verified

Thirteen of fourteen mutation forms discriminated across the
round-44 slate — the exhibits, the header budget on three surfaces,
the fold counts, the chain fold, the click budget, the per-scope
dictionary — and the sibling's own per-item mutation records all
reproduced. Suite: **4,014 passed, 0 failed** (with Chromium
present, so the browser clauses really ran); lint clean; all
markers agree. The self-filed UX-322/323 are real and sound (the
architecture's command table re-inventoried at 12 native + 19
aliases; round 41's falsified page-composition claim annotated in
place, with the three dated-but-true old measurements deliberately
left alone — a distinction worth having written down). The one
evasion found live is filed as **UX-332**: the nested-scrollbox
guards stop at the first matching CSS rule, so a second
`main .map-table` scroll rule appended later — which wins the
cascade in a real browser — restored the round-44 defect with
every guard green.

## The walk

Fifteen frictions, four of them genuine bugs, none previously
filed — which after forty-four rounds of feature audits is the
method's own finding: the guides had never been *walked*.

The bugs: `bga snapshot` on a bst-less machine — the README's
first real command — dies in a thirty-line traceback and leaves a
debris snapshot the store then describes wrongly and denies by
prefix (`UX-324`); `bga snapshot --aggregate` crashes with
`ModuleNotFoundError` on every plain pip install (a `from
tools.bga_snapshot import` that only resolves in a contributor
checkout — the wheel-shape class, recurring; `UX-325`); the
report's own "Next:" block prints a command the tool's parser
rejects, and running it deposits more debris (`UX-326`); and
`compare` prints "(--allow-mismatch was given…)" when no flag was
passed (`UX-326`'s second half).

The drift: four documented invocations that do not exist —
`cache-logs`' positional story in two docs, the departed
`--native-report`, `capture census` and `capture replay-sandbox` —
plus contradictory install instructions and a help text citing a
nonexistent guide (`UX-327`); the `--schema` story contradicting
itself three ways, refusing contracts for payloads the same page
shows emitting them (`UX-328`).

The seams: `analyze` and `view` disagree about Plane 2 on the same
run, against `view --help`'s explicit never-disagree promise, and
the absence grammar cannot distinguish "not captured" from
"captured, raw log not kept" (`UX-329`); the no-bst newcomer has
no committed path into `timeline` or the store loop at all — empty
scaffold stores, the one real fixture hidden in an appendix, and
`capture report` refusing its own committed fixture (`UX-330`);
the README excerpt elides the report's first Key Finding, which
itself reads as a self-contradiction until you know the unstated
90% threshold (`UX-331`).

And what the walk found working is worth the record: `doctor`'s
remedies read like lived experience; `whatif` matched the guide's
pasted figures to the millisecond; the alias errors match the
guide's promised wording verbatim; `--explain` is, in the
stranger's words, the best evidence-chain rendering they had seen
in a CLI. The read half of the loop is genuinely good — the walk
broke on the seams between it and the world: installation shape,
missing tools, empty stores, and sentences nobody had ever run.

## Filed

`UX-324` (the capture that cannot start, High), `UX-325` (the
user-install crash, High), `UX-326` (printed sentences as
contracts, High), `UX-327` (the four ghost invocations, High),
`UX-328` (--schema answers for everything that emits, Medium),
`UX-329` (the Plane 2 disagreement, High), `UX-330` (the
stranger's seed, Medium), `UX-331` (the excerpt and the
self-contradicting sentence, Low), `UX-332` (the cascade evasion
and two record nits, Medium).

## Standing

Priority: **UX-324, UX-325, UX-326 first** — two crashes and a
traceback on paths the docs actively promote, all three cheap;
then **UX-327 and UX-329** (the ghost invocations and the
never-disagree promise), then UX-328/330/332, with UX-331 as
polish. The round's lesson for the loop itself: feature audits
verify what was built; only a walk verifies what was *promised*.
The stranger protocol found four bugs forty-four feature rounds
missed, and it should recur — not every round, but on the cadence
the standing reviews already have.
