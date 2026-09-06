# UX-721: an aliased import is silently dropped by the export

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-199 (which derived the module order), UX-669 (which hit it) | **Serves:** anyone editing a viewer module | **Topic:** viewer | **Shape:** judgement | **Area:** tools

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
