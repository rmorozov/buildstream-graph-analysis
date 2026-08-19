# UX-124: close UX-104's fdsdk clause with the capture that can

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-104 (done, one clause honestly unattainable at the time), UX-108 (whose capture makes it attainable)

## Motivation

UX-104's acceptance named an fdsdk check — the envelope computed from
the real 1902 MB peak, matching the README's hand multiplication — and
recorded it as unattainable because the retained captures predate
`host_memory_mb`. One day later, UX-108's capture (run 32223468993)
shipped **with** the field, and nobody went back. Round 12 ran the
clause against that capture and it works:

```text
Memory: 4 builders of this shape peak at ~4.0 GB of 15.6 GB (25%);
11 would still fit at ~4.8 GB, so memory is not what binds first here
```

Meanwhile `README.md:298` still performs the hand multiplication
("multiply by however many elements build concurrently…") that UX-104
exists to replace.

## Required Fix

Paste the fdsdk envelope run into UX-104's verification log, closing
its open clause; replace the README's hand-multiplication sentence with
the tool's own envelope line from the same capture (with provenance,
per style rule 4).

## Out of Scope

- Any envelope logic change.

## Acceptance Test

UX-104's file shows the fdsdk clause closed with the pasted output;
`grep -n 'multiply by' README.md` returns nothing; the README's
replacement line quotes the capture it came from.

---

## Fix Implemented

`UX-104`'s verification log now carries the fdsdk envelope run, and the
README shows the tool's own line where it used to hand the reader a
multiplication:

```text
Memory envelope: 4 builders of this shape peak at ~4.0 GB of 15.6 GB (25%); 11 would
still fit, so memory is not what binds first here
```

with the capture named (run `32223468993`) and the upper-bound caveat
attached, per style rule 4.

No logic changed, and none needed to: the fallback that produces
*"multiply by however many elements build concurrently"* already fires
only when a capture records no host memory, and says so. The README's
sample was simply older than the capability.

**The pattern worth keeping.** `UX-104` recorded a clause as
unattainable, correctly, on the evidence then available — and the
evidence arrived the next morning. "Unattainable" is a claim about the
data on hand rather than about the world, and it expires; a filing that
records *why* it was unattainable is what let round 12 notice that the
reason had gone away.

## Verification Log

Done 2026-08-19. The envelope line is a live re-run of `bga correlate`
against the retained capture, not a paste from round 12's notes.
