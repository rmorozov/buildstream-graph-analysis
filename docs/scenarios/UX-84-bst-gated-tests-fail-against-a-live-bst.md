# UX-84: the bst-gated tests fail against a live bst 2.7, and CI never runs them

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-22 (done)

## Motivation

With BuildStream 2.7.0 + buildstream-plugins genuinely installed (this
round, clean venv, real `bwrap`), `make test` fails:

```
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
