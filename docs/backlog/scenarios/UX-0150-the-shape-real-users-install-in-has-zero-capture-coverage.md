# UX-150: the shape real users install in has zero capture coverage

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-77 (the packaging job this extends)

## Motivation

The first real external deployment installs `bga` from a repo checkout
in one directory into the venv of a project in another — and round 15
had to reproduce that shape by hand to discover it **works**: wheel →
fresh venv (with its own bst + plugins) → `bga snapshot` on a project
elsewhere, cwd elsewhere, no `PYTHONPATH` — full capture, both planes,
store, auto-compare. That is good news with no guard: every capture CI
has ever run is from the repo checkout with the repo's own layout, and
UX-77's packaging job stops at `--help` from an empty directory. The
one configuration users actually deploy is the one configuration no
test captures in — so the next `_bwrap_shim_source`-style path
assumption ships unnoticed, and the next field report starts from
zero again.

The install docs have the same gap: README's Install says
`pip install -e .`, which presumes cwd is the checkout and quietly
suggests editable is the supported mode. The deployed mode — *install
this repo into your project's venv* — is documented nowhere.

## Required Fix

1. **CI**: the packaging job (or a sibling) runs a real end-to-end
   capture from the installed wheel — clean venv with
   `bst`/`buildstream-plugins`, a copy of `examples/06` outside the
   checkout, cwd outside both, `bga snapshot -- bst build all.bst`,
   asserting the store, both planes' artifacts, and the diagnostics
   count (UX-146's "ran N times" is the cheap whole-chain assertion).
   This is the bst-examples machinery pointed at the wheel instead of
   the checkout.
2. **Docs**: README Install gains the deployed form first —
   `pip install /path/to/bga-checkout` (or the git URL) *into your
   project's venv* — with `-e .` framed as the contributor mode;
   `real-project.md`'s prerequisites say the same in one line.

## Out of Scope

- Publishing to PyPI (a product decision; the path form works today).
- The field failure's root cause (UX-147..149 carry the diagnostics).

## Acceptance Test

The CI step exists and is red when a capture-path regression is
injected (verify by mutation: point `_bwrap_shim_source` at a
repo-relative path and watch the wheel job fail while the checkout
jobs stay green — the exact class this guards). README shows the
deployed install first; the docs-commands test covers the new lines.
