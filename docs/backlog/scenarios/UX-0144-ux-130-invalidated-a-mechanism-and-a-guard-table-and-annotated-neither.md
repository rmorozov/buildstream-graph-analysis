# UX-144: UX-130 invalidated a mechanism and a guard table, and annotated neither

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-132 (the convention this extends), UX-130

## Motivation

UX-132 wrote the annotate-what-you-invalidate convention into the
fixing guide — scoped to "a number an earlier task file quotes". The
very next range demonstrated the scope is too narrow: UX-130 deleted
UX-118's entire mechanism (`g_seen`/`first_stop_for`/`forget_pid` —
the seen-set UX-118's Fix Implemented still describes as shipped) and
UX-128's `initial` site (its five-hang verification table, its row),
and `git diff` over UX-0106/0117/0118/0119 in that range is empty.
UX-118 is *itself the precedent UX-132 cites* — the convention's own
worked example was left describing dead code by the round that wrote
the convention down.

Also in-range bookkeeping the same class covers: UX-130's log says
"bst tier 34" while its own commit set the pin to 36; UX-128's log
pastes counts that don't reconcile without a skip line; and UX-106's
row still points its "open inch" at UX-128's then-future in-sandbox
clauses, which have since landed — its 🟡 needs reconciling against
its own stated return condition (the clauses now run in-sandbox;
what remains open, if anything, should be named or the status closed).

## Required Fix

1. Annotate UX-118 (mechanism deleted, superseded by SEIZE — old text
   kept, one line naming UX-130) and UX-128 (the `initial` site,
   coordinated with UX-141's code change) per the convention.
2. Widen fixing-guide item 5 from "a number" to "a number **or a
   mechanism/explanation** an earlier task file presents as current" —
   which is what the UX-106/UX-118 precedent it cites actually was.
3. Fix the two stale counts in UX-130/UX-128's logs; reconcile
   UX-106's status against its return condition.

## Out of Scope

- Automating this (judgment-shaped; the checklist mechanic stands).

## Acceptance Test

The two annotations exist and name UX-130; the fixing guide's item 5
covers mechanisms with the precedent named; `grep -n '34' UX-0130*`
finds no unannotated stale pin; UX-106's status line and row agree
with its own return condition, whichever way it resolves.
