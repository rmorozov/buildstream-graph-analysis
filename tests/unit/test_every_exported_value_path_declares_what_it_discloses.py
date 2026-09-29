"""UX-1060: every value path a fixture's bundle member holds has a class.

Walks every member of every fixture under `tests/fixtures/` against
`bga.disclosure`'s policy for its contract; an unnamed path, a class B
value off an allowlist with no fallback, or a contract with no policy
is a red naming it.
"""

import json
import pathlib

import pytest

from bga import disclosure

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures"
MEMBERS = disclosure.layout_members()
_BY_NAME = {pathlib.PurePosixPath(m).name: m for m in MEMBERS}


def _documents(path: pathlib.Path) -> list:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return [json.loads(text)]


def _fixture_members() -> list:
    found = []
    for path in sorted(FIXTURES.rglob("*")):
        member = _BY_NAME.get(path.name)
        if path.is_file() and member and disclosure.TREATMENTS.get(member) == disclosure.TRANSFORM:
            found.append((path.relative_to(REPO).as_posix(), member))
    return found


FIXTURE_MEMBERS = _fixture_members()


def test_the_fixtures_hold_every_contracted_transform_member():
    held = {member for _path, member in FIXTURE_MEMBERS}
    assert held >= {
        "run/graph.json",
        "run/trace.json",
        "run/run-context.json",
        "run/sources.json",
        "plane2.json",
        "host-samples.jsonl",
    }, held


@pytest.mark.parametrize("relative,member", FIXTURE_MEMBERS, ids=[p for p, _m in FIXTURE_MEMBERS])
def test_every_path_a_fixture_member_holds_is_named(relative, member):
    gaps = disclosure.gaps(member, MEMBERS[member], _documents(REPO / relative))
    assert not gaps, f"{relative} ({MEMBERS[member]}):\n" + "\n".join(map(str, gaps))


def test_every_layout_member_states_its_treatment():
    assert set(disclosure.TREATMENTS) == set(MEMBERS)
    unpoliced = [
        m
        for m, t in disclosure.TREATMENTS.items()
        if t == disclosure.TRANSFORM and disclosure.policy_key(m, MEMBERS[m]) not in disclosure.POLICIES
    ]
    assert not unpoliced


def test_every_class_names_one_of_the_eight_or_a_vocabulary():
    for policy in disclosure.POLICIES.values():
        for pattern, klass in policy.items():
            keys = [s[1:-1] for s in disclosure._parse(pattern) if s.startswith("{")]
            for named in [klass, *keys]:
                assert (named in disclosure.CLASSES and named != "B") or (
                    named.startswith("B:") and named[2:] in disclosure.VOCABULARIES
                ), (pattern, named)


def _run_context() -> dict:
    return _documents(FIXTURES / "host_cpu" / "run" / "run-context.json")[0]


def test_an_added_key_is_named_by_its_path():
    document = _run_context()
    document["host_manifest"]["codename"] = "falcon"
    gaps = disclosure.gaps("run/run-context.json", "run-context/v9", [document])
    assert [g.path for g in gaps] == ["host_manifest.codename"]


def test_a_class_b_value_off_its_allowlist_without_fallback_is_named():
    document = _documents(FIXTURES / "host_cpu" / "run" / "graph.json")[0]
    document["elements"][0]["element_kind"] = "acme_private_kind"
    gaps = disclosure.gaps("run/graph.json", "graph/v9", [document])
    assert ["acme_private_kind" in g.reason for g in gaps] == [True]


def test_a_class_b_value_with_a_fallback_is_not_refused():
    document = _run_context()
    document["host_manifest"]["toolchain"]["acme-cc"] = "acme-cc 9.1"
    assert not disclosure.gaps("run/run-context.json", "run-context/v9", [document])


@pytest.mark.parametrize(
    "vocab,value,admitted",
    [
        ("toolchain", "cc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0", True),
        ("toolchain", "bubblewrap 0.9.0", True),
        ("toolchain", "2.7.0", True),
        ("toolchain", "acme-cc 9.1", False),
        ("tool", "bwrap", True),
        ("tool", "acme-cc", False),
        ("binary", "cc1plus", True),
        ("binary", "acme-gen", False),
    ],
)
def test_a_fallback_vocabulary_keeps_public_values_and_only_those(vocab, value, admitted):
    assert disclosure.VOCABULARIES[vocab].admits(value) is admitted


def test_an_unknown_contract_version_reports_the_whole_member():
    gaps = disclosure.gaps("run/run-context.json", "run-context/v10", [_run_context()])
    assert [g.path for g in gaps] == [""]
