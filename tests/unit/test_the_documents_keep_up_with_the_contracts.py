"""UX-233: the architecture document meets the viewer axis.

The user's observation: *we frequently forget to update architecture and
specification documentation, which later increases the cost of big
refactoring.* Measured when this was filed: `design/architecture.md`
described three analysis planes and stopped at round 20 - before the
whole viewer axis and before the contract wave that followed it - and
the published-payload inventory, which is the tool's actual external
surface, existed only as the sum of `--schema` outputs.

The guard below is the part that survives good intentions. A new
published schema without a line in the spec and a line in the
architecture inventory reddens it, which is the only mechanism this
repository has ever found that keeps two hand-maintained copies of one
fact together (`UX-131`, and every round since).

holds: rules.md#architecture-or-spec-made-wrong-same-commit
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
ARCHITECTURE = REPO / "docs/design/architecture.md"
SPEC = REPO / "docs/spec/specification.md"
CLI_GUIDE = REPO / "docs/guides/cli.md"

# `UX-628`: the keys already carrying no prose when the population below
# went from ids to keys. Frozen, and it may only shrink - a key added
# after that item is not in here and reddens the clause naming it. Not
# an exemption anyone may extend: `test_the_register_is_all_live_keys`
# refuses a name that is no longer a key, so it cannot rot or be padded
# with a spelling that guards nothing.
UNDOCUMENTED_WHEN_THE_POPULATION_BECAME_KEYS = frozenset({
    "also_matched", "assembling_count", "attribution_deltas",
    "attribution_hints", "attribution_partial", "attribution_unreliable",
    "baseline_confidence", "baseline_run_id", "batch_opportunities",
    "blast_count", "blast_elements", "blast_radius_distribution",
    "blended", "bottleneck", "building_count", "by_element_kind",
    "cache_churn", "cache_hit_rate", "calls", "candidate_confidence",
    "candidate_run_id", "claim", "configure_phase",
    "consolidation_candidates", "copy_text", "cpu_share", "cpu_time",
    "deltas", "detail", "direct_count", "direct_elements", "edges",
    "element_count", "element_deltas", "element_duration_distribution",
    "element_exists", "element_join_coverage", "excluded",
    "excluded_runs", "failed_runs", "follows_from", "governing_cores",
    "granularity", "has_inventory", "host_class", "host_classes",
    "joint_saving", "keying", "label", "latent_heavies", "leads_with",
    "low_confidence", "measured_elements", "mismatches",
    "native_findings", "note", "pinned_elements",
    "process_count_distribution", "projection", "reason",
    "redundancy_count", "resolved_as", "resource_blast",
    "resource_pressure", "resource_shortfall", "sandbox_tax_distribution",
    "serialization_point_risks", "service", "shown", "snapshot_bytes",
    "stamps", "stamps_total", "store_bytes", "title", "total_bytes",
    "trace_queries", "typical_max_jobs", "unused_dependencies",
    "wall_us", "worst_redundancy",
})


def _published_schemas():
    """Every schema id the code stamps a document with.

    This used to be `schemas.names()` unioned with one hard-coded id,
    and `UX-248` measured what that costs: `sources/v1` - written to
    `sources.json` in every run directory and read back - was in no
    registry and therefore in no document. A union with a literal only
    ever covers the contracts someone remembered. `contracts.ids()`
    derives the set from the package.
    """
    from bga import contracts

    return contracts.ids()


GUIDES = REPO / "docs/guides"


def _consumer_surface():
    """`{key: [contract, ...]}` - the keys a consumer of a printable
    document meets.

    Each schema's top-level properties, plus the properties of a row
    directly under a top-level array: a row of `store/v1`'s `snapshots`
    is what a reader actually holds, and `queue_wait_us` lives only
    there. Not the full recursive key set - that is 891 keys, most of
    them internal shapes of one block, and a document naming all of
    them would be the second copy of the schemas `UX-384` already
    banned from the inventory.
    """
    from bga import contracts, schemas

    found = {}
    for name in contracts.printable():
        properties = schemas.schema(name).get("properties", {})
        keys = set(properties)
        for value in properties.values():
            if isinstance(value, dict) and isinstance(value.get("items"), dict):
                keys |= set(value["items"].get("properties", {}))
        for key in keys:
            found.setdefault(key, []).append(name)
    return found


def code_spanned(text):
    """Every identifier `text` writes in code font.

    Code font rather than a bare substring, which is the proxy this
    would otherwise be: `note`, `label` and `calls` occur in English on
    most pages of this repository, so a substring scan would report
    them documented and could not tell prose from a payload key. Pure,
    so its discrimination is a testable claim rather than an intention
    - loosening it only *shrinks* the undocumented set, which no clause
    over that set can notice.
    """
    found = set()
    for span in re.finditer(r"`([^`\n]+)`", text):
        found.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", span.group(1)))
    return found


def _named_in_the_documents():
    """`code_spanned` over the documents, less the ones that argue.

    `docs/backlog/` and `docs/audits/` are excluded because a task file
    naming the key it added is the argument, not the document - the
    failure mode the `falsify` skill calls *the guard that matches its
    own explanation*.
    """
    text = []
    for path in sorted(REPO.glob("docs/**/*.md")):
        relative = path.relative_to(REPO).as_posix()
        if relative.startswith(("docs/backlog/", "docs/audits/")):
            continue
        text.append(path.read_text(encoding="utf-8"))
    text.append((REPO / "README.md").read_text(encoding="utf-8"))
    return code_spanned("\n".join(text))


def _undocumented_keys():
    """The consumer surface less what the documents name."""
    named = _named_in_the_documents()
    return {key: where for key, where in _consumer_surface().items()
            if key not in named}


class TestThePopulationIsKeysAndNotIds:
    """`UX-628`. The clauses above guard contract **ids**, which is
    `UX-233`'s mechanical half doing exactly what it promised: five
    keys shipped in one window - `verdict_provenance`, `queue_wait_us`,
    `queue_wait_absent_reason`, `requested_at_us`,
    `requested_at_source` - and no document outside the backlog named
    any of them, with every clause above green.

    Full key coverage was measured before it was chosen and declined:
    199 surface keys, 84 of them undocumented. A guard demanding prose
    for all of them would be red on arrival and silenced. This is the
    ratchet instead, and the six clauses below are what stop a
    ratchet from being an off switch.
    """

    def test_prose_about_a_key_is_not_the_key(self):
        """The instrument, not the corpus. A looser match only shrinks
        the undocumented set, and every clause below is a claim *about*
        that set - so swapping code font for a bare word scan reddens
        nothing there and would silently retire the ratchet. Measured:
        that exact mutation left all six clauses green.

        `note`, `label`, `calls`, `reason` and `title` are real keys of
        real contracts and ordinary English words, which is why the
        difference has to be read rather than assumed.
        """
        assert code_spanned("the note explains the reason") == set()
        assert code_spanned("`note` is a key") == {"note"}
        assert code_spanned("`queue_wait_us`") == {"queue_wait_us"}
        # A fenced block is code font too, and its keys count.
        assert "label" in code_spanned('a row: `{"label": null}`')

    def test_a_new_key_with_no_prose_reddens_naming_the_key(self):
        """The item's Acceptance Test. A key not in the frozen register
        and named in no document fails here, by name."""
        undocumented = _undocumented_keys()
        new = {key: where for key, where in undocumented.items()
               if key not in UNDOCUMENTED_WHEN_THE_POPULATION_BECAME_KEYS}
        named = sorted("{} ({})".format(key, ", ".join(where))
                       for key, where in new.items())
        assert new == {}, (
            f"published key(s) no document names: {named}. "
            f"Name it where a consumer looks - docs/guides/cli.md's "
            f"contract section, or the row in docs/design/architecture.md's "
            f"inventory - or the payload ships undescribed (UX-628)")

    def test_the_population_is_large_enough_to_mean_something(self):
        """Non-vacuity for the clause above. The register is an
        exclusion, and an exclusion drawn too wide does not fail a
        clause - it removes the clause's input and the clause passes
        on an empty set. This reads the two sizes rather than trusting
        that they differ."""
        surface = _consumer_surface()
        assert len(surface) >= 150, (
            f"the consumer surface is {len(surface)} keys; it was 199 when "
            f"this was written, so either a contract stopped resolving or "
            f"the walk above stopped descending")
        checked = set(surface) - UNDOCUMENTED_WHEN_THE_POPULATION_BECAME_KEYS
        assert len(checked) >= 100, (
            f"the register excuses all but {len(checked)} of "
            f"{len(surface)} keys - the clause above is checking almost "
            f"nothing")

    def test_the_register_is_all_live_keys(self):
        """It cannot rot and it cannot be padded. A name in it that no
        contract carries is either a key that was renamed - and whose
        replacement then needs prose - or a spelling somebody added to
        quiet the clause above, and both read the same from here."""
        surface = set(_consumer_surface())
        stale = sorted(UNDOCUMENTED_WHEN_THE_POPULATION_BECAME_KEYS - surface)
        assert stale == [], (
            f"the register names key(s) no contract carries: {stale}. Drop "
            f"them - a register entry for a key that does not exist excuses "
            f"nothing and hides that the register may only shrink")

    def test_the_register_only_shrinks(self):
        """The ratchet, and only the ratchet. 80 when `UX-628` froze
        it; documenting a key lowers this number and nothing may raise
        it. Whether an *undocumented* key is in the register is the
        clause above, asserted there and not restated here - one
        mutation that reddens two clauses has falsified one."""
        assert len(UNDOCUMENTED_WHEN_THE_POPULATION_BECAME_KEYS) <= 80, (
            f"the register holds "
            f"{len(UNDOCUMENTED_WHEN_THE_POPULATION_BECAME_KEYS)} keys "
            f"against the 80 UX-628 froze; it may only shrink")

    def test_the_guide_states_the_coverage_it_actually_has(self):
        """The other half of the Required Fix: where key-level coverage
        stops is said where a consumer looks, and the figure is read off
        the register rather than restated. `UX-295` established that a
        *guide* is where the reader of a payload looks - the spec and
        the architecture are where a maintainer does.

        **The subject is the section, not the file.** Written against
        the whole guide first and it could not fail: line 345 already
        names all three input contracts while describing what `bga
        analyze` reads, so the clause was green whatever the coverage
        section said. That is the `falsify` skill's own failure mode -
        a guard reading the argument instead of the subject.
        """
        section = CLI_GUIDE.read_text(encoding="utf-8").split(
            "### Which keys the prose names", 1)
        assert len(section) == 2, (
            "docs/guides/cli.md has no `### Which keys the prose names` "
            "section - a consumer has nowhere to read how far key-level "
            "coverage goes")
        body = section[1].split("\n## ", 1)[0].split("\n### ", 1)[0]
        count = len(UNDOCUMENTED_WHEN_THE_POPULATION_BECAME_KEYS)
        assert f"**{count} undocumented keys**" in body, (
            f"that section does not state the {count} keys the register "
            f"holds; the figure is derived, so it moves when a key is "
            f"documented")
        for stated in ("run-context/v9", "graph/v9", "trace/v9"):
            assert stated in body, (
                f"the section does not tell a reader that {stated}'s keys "
                f"are outside this coverage - an input contract has no JSON "
                f"Schema here, so no guard can enumerate it")

    def test_the_input_contracts_are_outside_the_population_on_purpose(self):
        """And it is asserted rather than assumed, because it is the
        reason two of the five keys `UX-628` found can only ever be
        prose. If an input contract ever gains a schema here, this
        fails and the exemption above is re-decided rather than
        inherited."""
        from bga import contracts, schemas

        for name in contracts.reads():
            with pytest.raises(KeyError):
                schemas.schema(name)
        assert set(contracts.reads()).isdisjoint(_consumer_surface().keys())


def test_every_printable_contract_has_a_home_in_the_guides():
    """`UX-295`: a *guide* is where the consumer of a payload looks.

    Review 3 counted homes and found `whatif/v1` named four times
    across the spec, the architecture and a direction - and **zero**
    times in `docs/guides/`. The command that produces it was
    documented (`UX-246`); the document it produces was not, so a
    consumer holding `{"schema": "whatif/v1", ...}` and grepping the
    guides found how to make one and nothing about reading it.

    The clauses above already asked whether every contract has a home.
    Their notion of home is the spec and the architecture - where a
    *maintainer* looks - which is why this gap sat under a green
    guard. This one asks the reader's question instead.

    **Printable only.** `bga.contracts.unprintable()` names the shapes
    a run directory carries rather than a subcommand emits - `host/v1`,
    `sources/v1`, `plane2/*`. No `--format json` hands one to anybody,
    so requiring a CLI guide entry for them would be asking the wrong
    document to explain them; the architecture is their home and the
    clauses above hold it.
    """
    from bga import contracts

    printable = set(contracts.ids()) - set(contracts.unprintable())
    assert printable, "no contract is printable; this guard checks nothing"

    text = "\n".join(path.read_text(encoding="utf-8")
                     for path in sorted(GUIDES.rglob("*.md")))
    missing = sorted(name for name in printable if name not in text)
    assert missing == [], (
        f"published contract(s) named in no guide: {missing}. A consumer "
        f"holding one greps docs/guides/ and finds the command that made "
        f"it, not the document they are reading")


def test_the_unprintable_shapes_are_not_required_to_be_in_a_guide():
    """The exemption is a decision, so it is asserted rather than
    assumed - and it fails if `unprintable()` ever empties, which would
    silently widen the clause above into something nobody chose."""
    from bga import contracts

    unprintable = set(contracts.unprintable())
    assert unprintable, "unprintable() is empty; the exemption above is moot"
    assert unprintable <= set(contracts.ids())
    assert "whatif/v1" not in unprintable, (
        "whatif/v1 is printable - `bga whatif --format json` hands it to a "
        "consumer - and exempting it would undo UX-295")


def test_every_published_schema_is_named_in_the_spec():
    """In **Part 32.5**, not merely somewhere in the file.

    The first version of this asked whether the id appeared anywhere in
    the spec, and deleting a row from 32.5's table left it green -
    every id is also mentioned in Part 32's opening block. A guard that
    a deletion walks past is not guarding the table it is about.
    """
    text = SPEC.read_text(encoding="utf-8")
    section = text.split("## 32.5 The published output schemas", 1)
    assert len(section) == 2, "the spec has no Part 32.5"
    body = section[1].split("\n## ", 1)[0]
    missing = [name for name in _published_schemas() if name not in body]
    assert missing == [], (
        f"published schema(s) Part 32.5 does not list: {missing}")


def test_every_published_schema_is_in_the_architecture_inventory():
    """The inventory is the tool's external surface in one place. A
    payload that reaches a consumer and appears in no document is the
    increased-refactoring-cost failure this item is about."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    inventory = text.split("## The published contracts", 1)
    assert len(inventory) == 2, (
        "architecture.md has no `## The published contracts` chapter - "
        "the inventory this guard exists to keep current")
    body = inventory[1].split("\n## ", 1)[0]
    missing = [name for name in _published_schemas() if name not in body]
    assert missing == [], (
        f"published schema(s) missing from the architecture inventory: "
        f"{missing}")


def test_the_inventory_names_no_schema_the_code_does_not_emit():
    """The other direction. A schema removed from the code leaves its
    line behind, and the line then documents nothing."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    body = text.split("## The published contracts", 1)[-1].split("\n## ", 1)[0]
    listed = set(re.findall(r"`([a-z-]+/v\d+)`", body))
    stale = sorted(listed - set(_published_schemas()))
    assert stale == [], (
        f"the inventory names schema(s) nothing emits: {stale}")


def test_the_architecture_document_covers_the_viewer_axis():
    """Rounds 21-26 built a server, a schema-driven page and an export,
    and the architecture document did not mention any of it."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert "## The viewer axis" in text, (
        "architecture.md has no viewer chapter - it still stops at "
        "round 20")
    chapter = text.split("## The viewer axis", 1)[1].split("\n## ", 1)[0]
    for landmark in ("bga view", "--export", "no-arithmetic"):
        assert landmark in chapter, f"the viewer chapter does not mention {landmark}"


def test_the_fixing_guide_asks_whether_the_documents_moved():
    guide = (REPO / "docs/contributing/fixing-guide.md").read_text(
        encoding="utf-8")
    assert "architecture.md" in guide and "same commit" in guide.lower(), (
        "the Definition of Done does not ask whether this change makes "
        "architecture.md or the spec wrong")


def test_the_inventory_points_at_schema_rather_than_copying_it():
    """One line each, linking to `--schema` as the source of truth. A
    chapter that reproduced the schemas would be a second copy to
    maintain, which is the defect this item is about, not the fix."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    body = text.split("## The published contracts", 1)[-1].split("\n## ", 1)[0]
    assert "--schema" in body, (
        "the inventory does not point a reader at the printed schema")
    # The failure this is really about: somebody pastes the schemas in,
    # and the chapter becomes the second copy the item exists to avoid.
    pasted = [marker for marker in ('"properties"', "$schema", '"type":')
              if marker in body]
    assert pasted == [], (
        f"the inventory reproduces schema internals ({pasted}) instead of "
        f"pointing at `--schema` - that is a second copy to maintain, "
        f"which is the defect, not the fix")
    # The bound is derived rather than a constant: it moves with the
    # inventory, so adding a contract does not redden this and pasting
    # a schema in still does. `UX-384` found it as a literal 60 against
    # a 20-contract inventory, which meant the twenty-first row tripped
    # a guard about *copying* by growing the table it is meant to
    # describe.
    from bga import contracts

    budget = 3 * len(contracts.ids())
    assert len(body.splitlines()) < budget, (
        f"{len(body.splitlines())} lines against a budget of {budget} "
        f"({len(contracts.ids())} contracts) - the inventory is meant to "
        f"be one line per contract, not a copy of them")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
