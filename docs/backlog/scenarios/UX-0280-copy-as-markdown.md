# UX-280: copy as markdown

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-279 | **Serves:** R8 — whose destination is a ticket, a PR body or a chat message | **Topic:** viewer

## Motivation

Reported: *"maybe it would be great to have copy as markdown."*

It is, and the argument is stronger than convenience. Every destination
a copied finding actually reaches renders Markdown: GitHub issues and PR
bodies (`UX-115`'s CI comment is already Markdown), Slack, and this
repository's own task files. What the page copies today is plain text
with tab-separated columns, so a pasted table arrives as a smear and the
reader retypes it.

Measured — what `Copy shown rows` puts on the clipboard for a
three-column table:

```text
element<TAB>duration<TAB>share
core.bst<TAB>19.05s<TAB>44.1%
lib-b.bst<TAB>4.00s<TAB>9.3%
```

(`<TAB>` is a literal tab on the clipboard; written out here because
this repository's docs lint refuses hard tabs, which is the same reason
the paste destination cannot be relied on to keep them.)


and what the same rows need to be, to survive the paste:

```markdown
| element | duration | share |
|---|---|---|
| core.bst | 19.05s | 44.1% |
| lib-b.bst | 4.00s | 9.3% |
```

The values are identical; only the framing differs, and the framing is
the whole difference between a paste that reads and one that does not.

`UX-224` chose plain text deliberately — *"a finding you can paste
anywhere"* — and that reasoning holds for a **finding**, which is prose.
It does not hold for a **table**, which has structure that plain text
discards.

## Required Fix

1. Table copy offers Markdown alongside plain text, with the current
   filter and sort applied — the same rows, the same `data-raw` values.
2. The choice is remembered for the session, so a reader pasting ten
   tables into one ticket chooses once.
3. Findings and commands keep their existing plain-text form by default;
   a finding is a sentence and a command must paste into a shell
   unmodified. Markdown for those is a separate question and not this
   item's.

## Out of Scope

- HTML or CSV on the clipboard. CSV is `--format csv`'s job and reaches
  the same data through a path that already exists.
- Re-deriving anything during the copy. The clipboard gets what the
  table holds; a copy that computes is a second analyzer.

## Acceptance Test

Copying a filtered, sorted table as Markdown yields a table whose rows
and order match the DOM, whose cells match `data-raw`, and which renders
as a table when pasted into a Markdown document.

## Outcome

🟢 Done (round 39). Every table offers Markdown beside JSON.

**A rendering, not a selection.** `rowsMarkdown` reads the same
`data-raw` values from the same rows in the same order that `rowJson`
already copies, so the two cannot disagree about what was shown — the
guard asserts exactly that, by comparing the two outputs row for row.
Numeric columns are right-aligned from the column's declared quantity,
and a `|` inside a value is escaped, because one would otherwise end the
cell and silently reshape the table.

**Remembered for the reader, not in the link.** `localStorage`, which is
where this page already keeps per-reader preferences and which `UX-211`
draws the line at: the fragment carries what a reader *shares*, storage
carries what they *prefer*. Both sides are wrapped, because an export
opened from a folder may get no storage at all and a page that threw
there would lose the report rather than the preference.

Findings and commands keep their plain-text form, as the item asks: a
finding is a sentence and a command must paste into a shell unmodified.
