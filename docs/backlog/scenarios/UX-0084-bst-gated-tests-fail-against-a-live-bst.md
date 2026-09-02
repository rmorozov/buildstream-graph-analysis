# UX-84: the bst-gated tests fail against a live bst 2.7, and CI never runs them

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-22 (done) | **Topic:** guards

## Motivation

With BuildStream 2.7.0 + buildstream-plugins genuinely installed (this
round, clean venv, real `bwrap`), `make test` fails:

```text
FAILED tests/unit/test_bst_extract_run.py::test_real_end_to_end_extraction_produces_a_complete_bga_ready_run - assert True is False
FAILED tests/unit/test_bst_show_to_graph.py::test_real_bst_show_against_fixture_project - assert False
FAILED tests/unit/test_bst_show_to_graph.py::test_real_bst_show_captures_per_element_max_jobs_override - assert 4 == 16
FAILED tests/test_e2e.py (chrome-trace event pairing on the fetch+build fixture)
4 failed, 1122 passed
```

The sharpest one: `manual.bst` declares a real `public: bst: max-jobs:
16` override, and the extractor returns **4 — the host core count** —
for it, and non-None for elements with no override. UX-22's per-element
max-jobs capture, which feeds the serialization-point detection and the
capacity checks, reads the resolved default instead of the declared
override against this bst version. Every downstream consumer silently
gets the wrong requested-jobs figure.

These tests are skip-gated on `bst` being present, and **no CI job runs
pytest with bst installed** — the `test` job has no bst, and the
`bst-smoke`/`bst-examples` jobs run builds, not pytest. So the entire
bst-gated tier can rot (or may never have passed against 2.7) with a
permanently green CI.

## Required Fix

1. Diagnose whether the max-jobs regression is a `bst show`
   format/semantics change in 2.7 or a bug in `_parse_max_jobs`'s
   `%{public}` reading, and fix the extraction (the fixture declares 16;
   the graph must record 16).
2. Fix or re-baseline the other three failures on 2.7 with the same
   scrutiny (each is a real-`bst` integration seam).
3. Add one CI matrix cell (single Python version is enough) that
   installs `.[bst]` + buildstream-plugins and runs pytest, so the gated
   tier actually gates.

## Out of Scope

- Supporting BuildStream versions other than the 2.x line CI pins.

## Acceptance Test

On a host with bst 2.7.0: `make test` passes with **zero** failures and
the max-jobs test asserts 16, not 4. The new CI job runs the previously
skipped tests (assert the collected-and-run count includes them) and is
red if any bst-gated test fails.

---

## Resolution (round 11)

**Status:** 🟢 Done

Installed BuildStream 2.7.0 + `buildstream-plugins` 2.7.0 into a clean
venv alongside a real `bwrap` and ran the suite. Two of the three
Required Fix items landed as written; the first did not, and the reason
matters.

### 1. The max-jobs "regression" is the correct answer, not a bug

The Required Fix says *"the fixture declares 16; the graph must record
16."* Recording 16 would record a number no build has ever used.

Measured against the live bst, on the fixture itself:

```text
$ bst show --deps none --format '%{public}' manual.bst
bst:
  max-jobs: 16
  split-rules:
    ...

$ bst show --deps none --format '%{vars}' manual.bst | grep max-jobs
max-jobs: 4                      # host core count; `nproc` = 4

$ bst show --deps none --format '%{vars}' base.bst  | grep max-jobs
max-jobs: 4                      # identical, and base.bst declares nothing
```

`public: bst: max-jobs: 16` really is in `%{public}` — and BuildStream
really does ignore it. `%{max-jobs}`, which is what the plugins expand in
`environment: JOBS: -j%{max-jobs}`, resolves to 4 for `manual.bst` and
for `base.bst` alike. `UX-22` settled on the `public:` route; `UX-31`
found the real one (`variables: notparallel: True`) and re-pointed the
extractor at `%{vars}`, keeping `public:` only as a fallback for
pre-UX-31 run directories. The extractor returning 4 is `UX-31` working.

What the assertion lost was the *discrimination* — it no longer proved
the capture can tell one element's parallelism from another's. So the
fixture gained `elements/notparallel.bst`, carrying the control
BuildStream honours:

```text
$ bst show --deps none --format '%{vars}' notparallel.bst | grep -E 'max-jobs|notparallel'
max-jobs: 1
notparallel: True
```

and the test now asserts that: `notparallel.bst` → 1, `base.bst` → the
host count, the two differ, and `manual.bst`'s `public:` override
reaches the graph as the host count rather than as 16. Asserting
`os.cpu_count()` rather than a literal `4` keeps it true on any runner.

**Deviation from the Required Fix, recorded deliberately:** item 1 asked
for the extraction to change so the graph records 16. It asked for the
wrong thing, on a premise `UX-31` had already overturned. The extraction
is unchanged; the assertion was re-baselined.

### 2. Nine of the ten failures were the harness, not the tool

The audit recorded four failures. In this container the same suite
produced **ten**. In a clean venv it produced **one**.

The nine were a harness bug. Every bst-gated test hands `bst` a
two-key environment built from scratch — `{"HOME": tmp, "PATH": ...}` —
to isolate BuildStream's cache. Python resolves per-user
`site-packages` *from `HOME`*, so on a machine where BuildStream was
installed with `pip install --user`, `bst` dies at startup:

```text
ModuleNotFoundError: No module named 'jinja2'
```

before it reads the project. The tests then failed on the *symptom* —
"Could not find a 'Targets:' line", `CalledProcessError` from
`bst source track` — pointing squarely at the tool.

Fixed in `tests/unit/_bst_env.py`: inherit the environment, override
only `HOME`, and carry the real user `site-packages` across via
`PYTHONPATH` when this interpreter is actually using one (None on the
common venv/system case, so nothing is added that isn't needed). The
isolation is unchanged — `HOME` is the only thing `bst` keys cache and
config off. Verified both ways: 1169 passed under the `--user` layout
that produced ten failures, and 1169 passed in the clean venv.

### 3. The one real failure

`test_real_end_to_end_extraction_produces_a_complete_bga_ready_run`
asserted `cpu_accounting_available is False`. Measured: `True`, with
`effective_cpus = 4.0` and `effective_cpus_source =
detected_host_cpu_count`.

`UX-17` widened that flag — it means "a real capacity value is
available", not "a `cpu_accounting` block was present" — and
`bga/utilisation/__init__.py:225-238` says so in as many words. P1-33's
actual rule survives intact and is what is asserted now: capacity is
never fabricated from a *scheduling parameter*. `builders` is also 4 in
this run, so a regression that went back to reading it would produce the
same `4.0`; only `effective_cpus_source` separates the honest answer
from the fabricated one, which is why it is the assertion.

The `tests/test_e2e.py` chrome-trace failure the audit listed did not
reproduce in either environment.

### 3b. The job found a real bug on its first run

The new job went red three times before it went green, and the third
failure was not in the job.

`test_single_real_build_captures_both_planes_and_combined_trace_correlates`
asserted **exactly one** outer `bst-builder` B event for `core.bst`. On
a fresh runner there were two:

```text
action=fetch  core.bst [.../9c77a3d5-fetch.<date>.log]
action=build  core.bst [.../9c77a3d5-build.<date>.log]
```

Plane 1 emits one B event per *task*, not per element, and an element
whose sources are not already cached gets a `fetch` task too. Every run
that had ever checked this assertion happened to be warm.

The stale assertion was hiding a **production bug**.
`compute_clock_offset_us` in `tools/native_trace_to_chrome_trace.py`
took the *first* matching B event and its docstring stated that was "the
only real per-element B event Plane 1 ever emits". On a cold cache it
anchors Plane 2's whole timeline to the **fetch** task instead of the
build - and Plane 2 only exists inside the *build* sandbox, so every
traced process lands early by the entire fetch duration. On
`examples/05` the error is 0 (its sources are `kind: local`); on a
project with real network sources a fetch is minutes.

Fixed to anchor on `args.action == "build"`, falling back to the first B
event only when the element has no build task at all. The test now
asserts the anchor *is* the build task's start, and injects a synthetic
fetch event 30s earlier to prove ordering cannot capture the anchor.
Verified by reverting the production fix: the guard fails with a 30s
error, exactly the bug.

Reproduced locally first by clearing the BuildStream cache — the same
failure this container had produced once during an earlier full-suite
run and which I had written off as transient interference from a
concurrent capture. It was this bug both times.

### 4. The CI gap, closed

The bst-gated tests now carry a `bst` marker (registered in
`pyproject.toml`) alongside their existing `skipif`, and a new
`bst-tests` CI job installs `.[dev,bst]` + `buildstream-plugins` +
bubblewrap + a C toolchain and runs them.

The job asserts the tier *ran*, not merely that nothing failed: a skip
exits 0 and reads as a pass, which is precisely how this rotted. It
greps its own output for `SKIPPED` and pins the count at exactly 14, so
growing the tier is a deliberate edit rather than a silent drift. It
then runs `make test` in full, because an extraction change can break an
unmarked test only when a real bst produced the input.

### Acceptance

- `pytest` against bst 2.7.0 in a clean venv: **1169 passed, 0 failed**.
- `pytest -m bst` at the time of this round: **14 passed, 1155 deselected** — zero
  skipped. (`UX-91` later added a fifteenth and moved CI's pin with it; the pin is
  now the only hand-written copy of that number and a test checks it against the
  marked tests — see `UX-97`.)
- `pytest -m "not bst"`: 1155 passed, 14 deselected (the marker
  partitions the suite exactly).
- The max-jobs test asserts the `notparallel` discrimination against a
  live `bst show`, and that 16 does *not* reach the graph.
- `make lint`, `make check-clean` green.
