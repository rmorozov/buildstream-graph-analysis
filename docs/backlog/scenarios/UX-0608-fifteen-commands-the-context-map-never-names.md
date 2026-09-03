# UX-608: fifteen commands the context map never names

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-590 (which measured it), UX-607 (which blocks it) | **Serves:** every session reading fixing guide §6 to find where a thing lives | **Topic:** docs

## Motivation

`UX-590` held §6's `--format` row against the writer registry both
ways. The command half it could only do in one direction — a command
*named* in §6 is checked against the registry, but the registry is not
held to appear in §6:

```text
registered commands            32
named nowhere in §6            15
--format choices                4     named in §6   2
```

The map's whole promise is "where does a thing live", and for
fifteen of thirty-two commands it does not answer.

## Required Fix

§6 names every registered command, and a guard holds the set both
ways — so adding a subcommand without a map entry is red, and a map
entry naming no command is red.

## Out of Scope

- The `--format` row — done in `UX-590`, and it is the worked example
  this one follows.

## Acceptance Test

A registered command removed from §6 — red naming it; a §6 entry for
a command that does not exist — red.

## Blocked on

`UX-607`. The vocabulary costs ~920 B against 33 B of headroom.
