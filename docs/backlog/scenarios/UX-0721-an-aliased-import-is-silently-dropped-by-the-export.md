# UX-721: an aliased import is silently dropped by the export

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-199 (which derived the module order), UX-669 (which hit it) | **Serves:** anyone editing a viewer module | **Topic:** viewer | **Shape:** judgement | **Area:** tools

## Motivation

`tools/bga_view.py:872` matches an import statement to find the module
it names, and `_inline_module` blanks the whole statement:

```python
_IMPORT_RE = re.compile(r"""^[ \t]*import\s.*?from\s+["']\./([\w.-]+)["'];?""",
                        re.M | re.S)
```

The modules then concatenate into one scope, where every `export` is a
top-level declaration. That is correct for `import { heading }` - the
name is already there - and wrong for `import { heading as headingOf }`,
which leaves `headingOf` declared nowhere. Measured on
`tests/fixtures/macro_micro`, exported and booted at 1440x900, with
`UX-669`'s first draft:

```text
#decision   <section class="verdict refused section-failed">
            "Its renderer threw on `report.json` ... ReferenceError:
             headingOf is not defined"
```

The whole decision panel - the first screen - replaced by `UX-335`'s
containment banner. The served page was fine: it is a real ES module
there, and the alias resolves.

No viewer module aliases an import today (`grep " as " bga/viewer/*.js`
at 0 hits on the import lines), which is why nothing has caught it.
`UX-669` renamed three locals to avoid the alias; the next round has no
reason to know it must.

## Required Fix

Either the export translates an alias - one `const headingOf = heading;`
per renamed binding, emitted where the statement was blanked - or a
guard refuses one, naming this file and the reason. The second is
cheaper and states the constraint where it bites; the first removes the
constraint. Pick one and say which in the Outcome.

## Out of Scope

- Default and namespace imports (`import x from`, `import * as x`).
  No viewer module has either, and `_module_order` would not walk them.

## Acceptance Test

Guard: a viewer module with an aliased named import either exports and
boots with the alias resolving, or the export refuses with a message
naming the module and the alias. Mutation: reintroduce
`import { heading as headingOf }` in `decision.js` - red, and the
message says which module.

## Outcome

**Refused, not translated.** The Required Fix left the choice open.
Translation — one `const alias = original;` where the statement was
blanked — removes the constraint, and it was the tempting answer until
the flattened scope was measured:

```console
$ # every top-level function|const|let|class in bga/viewer/*.js, by owner
modules 22   top-level names 393   # 394; see UX-729
collisions {'make': ['drawings.js', 'perfetto_page.js']}
```

The flattening breaks two ways, not one. Translating the alias fixes
the half `UX-669` hit and leaves the other silent, so the constraint
would be half-removed and still unstated. A refusal states it once,
where it bites, and covers only what it claims. The collision half is
filed as `UX-729` with the measurement above; it is not live (the
export inlines `app.js`'s 21 modules, which exclude `perfetto_page.js`,
and `perfetto.html` is served, where each module keeps its own scope).

**The gap, measured.** With `UX-669`'s first draft restored —
`import { childNode, heading as headingOf, hintsOf }` in `decision.js`
— on `examples/06-macro-micro-optimization`, before this change the
export wrote 467 KiB at exit 0 and the decision panel rendered as
`ReferenceError: headingOf is not defined`.

**The close, measured.** Same alias, same fixture, after:

```console
$ python3 -m bga.cli view <run> --export alias.html; echo exit=$?
exit=2
stdout   (empty)
stderr   Error: decision.js renames an import (heading as headingOf) and
         the export cannot carry it: the modules concatenate into one
         scope, the `import` line is dropped, and the alias resolves to
         a name nothing declares. Use the imported name unaliased and
         rename the local that clashes with it.
$ ls alias.html
ls: cannot access 'alias.html': No such file or directory
```

Unaliased, the export is unchanged: 21 modules, 478,548 B on the same
fixture. No module the export inlines renames an import today.

**The mutation table.** Five, each reddening a named clause in
`test_an_aliased_import_is_refused.py` (7 clauses).

| mutation | clause that reds |
|---|---|
| the refusal is removed (`if False`) | `..._raises_naming_the_module_and_the_alias` + `..._exits_non_zero_and_writes_nothing` |
| the message drops the module name | the same two |
| `_ALIAS_RE` loses `\b` and `\s+` | `..._a_name_merely_containing_as_is_not_a_rename` + `..._no_module_the_export_inlines_renames_an_import` |
| `decision.js` gains the alias again (data) | `..._no_module_the_export_inlines_renames_an_import` |
| the tree walk reads no module | the same |

**A sixth mutation found a vacuous clause of my own.** The first draft
split the statement at `from` before looking for ` as `, guarded by
`test_the_module_path_is_not_read_as_a_rename` on `from "./as.js"`.
Reading the whole statement instead left all nine clauses green: `as`
in a path is bounded by `/` and `.`, never by whitespace, so the split
defended nothing a real module name can reach. Split and clause both
removed rather than kept as decoration.

**Deviation: the refusal exits 2 and writes nothing.** The Acceptance
Test asked only that the export refuse. `UX-725`, closed the same day,
is the reason the guard also reads the exit code and the absent file —
a refusal that exits zero and leaves a page behind is what that item
was about.
