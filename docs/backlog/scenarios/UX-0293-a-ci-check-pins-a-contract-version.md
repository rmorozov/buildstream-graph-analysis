# UX-293: a CI check pins a contract version

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-276 | **Serves:** R8 — whoever has to trust a green build | **Topic:** guards

## Motivation

`UX-288` moved `analyze/v1` to `analyze/v2`. That was the point of the
item: fields were removed, `architecture.md`'s rule says a removal bumps
the version, and a guard asserts the new version deliberately. The full
suite was green at 3463 passed and `make lint` was clean.

CI went red anyway, in the one file the suite does not scan:

```text
.github/workflows/ci.yml:173
    assert d['schema']=='analyze/v1', d.get('schema')
AssertionError: analyze/v2
```

The step is the packaging job's smoke test — install a wheel, serve a
run through it, check that the page's assets and the payload come back.
Its purpose never needed the literal. It had one, so a deliberate
contract bump broke a check about packaging, and the failure arrived
from a runner rather than from the suite.

**This is `UX-276`'s shape again.** A rule everybody knows — the version
moves when a field is removed — with nothing mechanical behind it in the
places that are not Python. `UX-276` made the "a guard may not rest only
on a path git does not track" rule mechanical after the same class of
CI-only failure; the checks themselves were never swept.

## Required Fix

1. The packaging step reads the expected contract out of
   `bga/schemas.py` rather than carrying a copy of it, and keeps a
   non-circular assertion of its own (the payload has content).
2. A guard: no CI check names a contract version the tool does not
   currently declare. Prose may name a past version — `directions.md` is
   full of history and that is what it is for — but an executable check
   that pins one is a stale assertion waiting for the next bump.
3. The sweep reads what a runner *runs*, not the comments explaining it.
   The first draft failed on the comment written by this very fix, which
   is the thirteenth instance of the self-matching guard in this
   repository (`UX-239`).

## Out of Scope

- Whether the version should have moved. It should have, and `UX-288`'s
  guard asserts it on purpose.
- Contract literals in Python, which `UX-248`'s inventory already
  derives and cross-checks two ways.
- Prose. A document recording what `analyze/v1` published is a record,
  not a check.

## Acceptance Test

Planting `analyze/v1` back into `.github/workflows/ci.yml`'s assertion
reddens the suite, and a comment naming a past version does not.

## Outcome

🟢 Done (round 38), in the commit that found it.

**The fix.** The packaging step derives its expectation:

```bash
EXPECTED=$(python -c "import re,pathlib; \
  print(re.search(r'^ANALYZE = \"([^\"]+)\"', \
    pathlib.Path('$GITHUB_WORKSPACE/bga/schemas.py').read_text(), \
    re.M).group(1))")
```

and asserts against it, plus a claim the version literal never made —
that the served payload has content at all. Both halves were exercised
locally against the real block, pulled out of the YAML rather than
retyped:

```text
served analyze/v2 from the installed wheel        -> rc 0
a payload stamped analyze/v1                      -> rc 1
a payload with no signals                         -> rc 1
```

**The guard.** `tests/unit/test_a_check_does_not_pin_a_contract.py`
sweeps `.github/workflows/` for contract literals and fails on any the
tool does not currently declare. Falsified:

```text
M1 the workflow pins analyze/v1 again   -> 1 failed  (the real defect)
M2 the sweep stops reading .yml         -> 1 failed  (it looked nowhere)
M3 the step hardcodes EXPECTED again    -> 1 failed
M4 comment stripping becomes "contains" -> 1 failed
```

M4 did not discriminate at first: the case pinning "a comment is not a
pin" put the comment on its own line, so dropping every line *containing*
a `#` still left the code line standing. A pin written with a note after
it would have been invisible. The case now carries one.

**The thirteenth self-matching guard.** The first draft failed on the
comment written by this fix — the sentence saying the step *used to*
assert `analyze/v1` is not an assertion. The sweep reads what a runner
runs: a `#` line is a comment in YAML and a comment in the shell inside
a `run: |` block, so one rule covers both, and a test pins that a
comment naming a past version is not a pin while code naming one still
is.

**A process note, recorded because it cost real work twice this
round:** both times the fix was lost, it was to `git checkout <path>` on
a file whose change was not yet committed. `git checkout` discards; it
does not revert-to-my-edit. Mutation testing now runs only against a
committed tree.
