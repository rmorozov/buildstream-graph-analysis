"""UX-376: the census could not see the tool, and the policy believed it.

`bga snapshot` runs `--trace-spine=auto`, which asks the census whether
any element stages a statically-linked executable and turns the ptrace
spine on only where the answer is yes. `census_project` reads the
project's own `local` sources - files on disk before anything runs - so
a tool the build *produces* is outside it. Its own docstring said so.
The policy acted on the answer anyway.

Measured on a fixture built for the question: `hosttool.bst` produces
one `-static` executable and `consumer.bst` build-depends on it and
runs it 200 times.

```text
                              before, auto      --trace-spine=on      after, auto
processes traced                        21                   221              207
consumer.bst                             7                   207              207
codegen (the tool it ran)           absent                   200              200
```

and the sentence the capture printed while deciding:

```text
before  Census: 4 of 4 element(s) assessed, none with static binaries
        (the spine is not needed)
after   Census: 2 of 4 element(s) assessed, none of those staged a static
        binary; 2 stage what this build produces and cannot be assessed
        before it runs - those get the spine
```

"The spine is not needed" was printed for a run in which the spine was
the difference between 21 processes and 221.

**The rule.** An `import` element stages its sources verbatim, so the
census sees exactly what its sandbox will hold. Every other kind runs
commands and produces something new. An element whose declared build
closure contains a non-`import` element therefore has a sandbox the
census cannot assess before the build - and `census_spine_verdicts` was
*already* written to trace what it has no verdict for. It simply had no
unassessable elements to apply that rule to, because the census
answered for every element whether or not it could.
"""
import pathlib
import sys
import textwrap

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.bst_native_build_tracer import (
    census_project,
    census_spine_verdicts,
    format_census_coverage,
)


def _project(tmp_path, elements):
    """A project on disk with the given `{name: yaml}` elements."""
    (tmp_path / "project.conf").write_text(
        "name: fixture\nmin-version: 2.0\nelement-path: elements\n",
        encoding="utf-8")
    directory = tmp_path / "elements"
    directory.mkdir(exist_ok=True)
    (tmp_path / "files").mkdir(exist_ok=True)
    for name, body in elements.items():
        (directory / name).write_text(textwrap.dedent(body), encoding="utf-8")
    return str(tmp_path)


#: The shape the item is about: one element that *produces* a tool, and
#: one that depends on it and will run it.
PRODUCES_A_TOOL = {
    "toolchain.bst": """
        kind: import
        sources:
        - kind: local
          path: files
        """,
    "hosttool.bst": """
        kind: manual
        depends:
        - filename: toolchain.bst
          type: build
        """,
    "consumer.bst": """
        kind: manual
        depends:
        - filename: toolchain.bst
          type: build
        - filename: hosttool.bst
          type: build
        """,
}


class TestTheCensusSaysWhatItCouldNotAssess:
    def test_an_element_staging_only_imports_is_assessable(self, tmp_path):
        project = _project(tmp_path, PRODUCES_A_TOOL)
        census = census_project(project, sorted(PRODUCES_A_TOOL))
        entry = census["per_element"]["hosttool.bst"]
        assert entry["assessable"] is True
        assert entry["unassessable_because"] == []

    def test_an_element_staging_what_the_build_makes_is_not(self, tmp_path):
        project = _project(tmp_path, PRODUCES_A_TOOL)
        census = census_project(project, sorted(PRODUCES_A_TOOL))
        entry = census["per_element"]["consumer.bst"]
        assert entry["assessable"] is False
        assert entry["unassessable_because"] == ["hosttool.bst"], (
            "the census does not name which dependency it could not see "
            "through, so a reader cannot tell why the spine turned on")

    def test_the_census_publishes_the_set(self, tmp_path):
        project = _project(tmp_path, PRODUCES_A_TOOL)
        census = census_project(project, sorted(PRODUCES_A_TOOL))
        assert census["elements_unassessable"] == ["consumer.bst"]

    def test_unassessable_is_not_folded_into_at_risk(self, tmp_path):
        """Two different facts. "Something static is staged here" is a
        property of the project; "part of what will be staged here does
        not exist yet" is a limit of the instrument, and a reader does
        different things about them."""
        project = _project(tmp_path, PRODUCES_A_TOOL)
        census = census_project(project, sorted(PRODUCES_A_TOOL))
        assert census["elements_at_risk"] == []
        assert census["elements_unassessable"] == ["consumer.bst"]


class TestThePolicyActsOnWhatItCannotSee:
    def test_an_unassessable_element_gets_the_spine(self, tmp_path):
        project = _project(tmp_path, PRODUCES_A_TOOL)
        verdicts = census_spine_verdicts(project)
        assert verdicts["consumer.bst"] is True, (
            "the element that will run a build-produced tool is skipped by "
            "`auto` - which is the 21-of-221 capture this item is about")

    def test_an_assessable_clean_element_still_is_not_traced(self, tmp_path):
        """The other direction, so the fix is not "always on": a project
        whose elements stage only imports keeps paying nothing."""
        project = _project(tmp_path, PRODUCES_A_TOOL)
        verdicts = census_spine_verdicts(project)
        assert verdicts["hosttool.bst"] is False
        assert verdicts["toolchain.bst"] is False


class TestTheSentenceMatchesTheVerdict:
    def test_it_does_not_claim_the_spine_is_unneeded(self, tmp_path):
        project = _project(tmp_path, PRODUCES_A_TOOL)
        verdicts = census_spine_verdicts(project)
        line = format_census_coverage(
            project, verdicts,
            getattr(census_spine_verdicts, "last_unassessable", None))
        assert "the spine is not needed" not in line, (
            f"an unqualified claim on a project the census cannot assess: "
            f"{line}")
        assert "cannot be assessed" in line, line
        assert "those get the spine" in line, line

    def test_it_counts_the_two_reasons_apart(self, tmp_path):
        project = _project(tmp_path, PRODUCES_A_TOOL)
        verdicts = census_spine_verdicts(project)
        line = format_census_coverage(
            project, verdicts,
            getattr(census_spine_verdicts, "last_unassessable", None))
        # Two of the three declared elements are assessable; one is not.
        assert "2 of 3 element(s) assessed" in line, line
        assert "1 stage" in line or "1 stages" in line, line

    def test_a_fully_assessable_project_keeps_its_old_sentence(self, tmp_path):
        """`UX-160`'s line, unchanged where the census can answer."""
        only_imports = {"a.bst": """
            kind: import
            sources:
            - kind: local
              path: files
            """}
        project = _project(tmp_path, only_imports)
        verdicts = census_spine_verdicts(project)
        line = format_census_coverage(
            project, verdicts,
            getattr(census_spine_verdicts, "last_unassessable", None))
        assert "cannot be assessed" not in line, line
        assert "1 of 1 element(s) assessed" in line, line
        # `UX-160`'s all-clear too, and this is the direction the first
        # draft of this item lost: the parenthetical was removed from
        # every sentence rather than from the ones that cannot support
        # it, so the case where it is *true* stopped saying so. The
        # census saw the whole project here - nothing deferred, nothing
        # skipped - which is exactly when the claim is sound.
        assert "the spine is not needed" in line, line

    def test_the_all_clear_needs_the_whole_project_seen(self, tmp_path):
        """And the other direction, on one project rather than two:
        add an element the census cannot assess and the parenthetical
        goes, while the elements it *could* read are unchanged."""
        mixed = {"a.bst": """
            kind: import
            sources:
            - kind: local
              path: files
            """}
        mixed.update(PRODUCES_A_TOOL)
        project = _project(tmp_path, mixed)
        verdicts = census_spine_verdicts(project)
        line = format_census_coverage(
            project, verdicts,
            getattr(census_spine_verdicts, "last_unassessable", None))
        assert "the spine is not needed" not in line, (
            f"the all-clear survives an element the census could not "
            f"read: {line}")
        assert "cannot be assessed" in line, line

    def test_the_all_clear_needs_a_verdict_for_every_declared_element(
            self, tmp_path):
        """The third way the census can fall short, and the one a
        mutation sweep found this clause did not cover: an element that
        is *declared* and got no verdict at all. That is neither a
        static binary nor something the build produces - it is an
        element the walk never reached - and `auto` traces it, so the
        all-clear would be claiming the spine is unneeded for elements
        it is about to run on."""
        only_imports = {"a.bst": """
            kind: import
            sources:
            - kind: local
              path: files
            """, "b.bst": """
            kind: import
            sources:
            - kind: local
              path: files
            """}
        project = _project(tmp_path, only_imports)
        verdicts = census_spine_verdicts(project)
        assert len(verdicts) == 2, verdicts
        # One declared element with no verdict: the shape `unassessed`
        # counts, reached here by handing the formatter a short dict
        # rather than by breaking the census.
        partial = dict(list(verdicts.items())[:1])
        line = format_census_coverage(project, partial, set())
        assert "unassessed" in line, line
        assert "the spine is not needed" not in line, (
            f"the all-clear survives a declared element with no verdict: "
            f"{line}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
