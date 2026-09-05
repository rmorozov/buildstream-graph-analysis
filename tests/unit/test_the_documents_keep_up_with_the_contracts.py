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

# `UX-628` froze the 80 keys already carrying no prose when this
# population went from ids to keys; `UX-636` documented all 80 and the
# register is empty. It stays as a name rather than being deleted: the
# clauses below are the statement it became, and an entry reappearing
# here is a debt that has to be argued rather than added.
UNDOCUMENTED_WHEN_THE_POPULATION_BECAME_KEYS = frozenset()


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
BACKLOG = REPO / "docs/backlog/scenarios"
PART_32 = "# Part 32 — Data Contracts"


def _part_32_opening_block():
    """`[(ids, annotation)]` for Part 32's opening fenced block.

    Anchored on the Part heading and closed at the first subsection, so
    the subject is the block a reader of the spec meets first - not
    32.5's table 117 lines below, which
    `test_a_counted_figure_is_derived.py` reads and which `UX-651`
    measured two ids ahead of this block.
    """
    text = SPEC.read_text(encoding="utf-8")
    parts = text.split(PART_32, 1)
    assert len(parts) == 2, f"the spec has no `{PART_32}` heading"
    fenced = parts[1].split("\n## 32.", 1)[0].split("```")
    assert len(fenced) >= 3, "Part 32 opens with no fenced block"
    rows = []
    for line in fenced[1].splitlines():
        if "(" not in line:
            continue
        names, annotation = line.split("(", 1)
        rows.append((re.findall(r"[a-z][a-z0-9-]*/v\d+", names),
                     annotation.strip().rstrip(")")))
    return rows


def _part_32_subsections():
    """Every id Part 32 gives a numbered subsection of its own."""
    text = SPEC.read_text(encoding="utf-8")
    return set(re.findall(r"\n## 32\.\d+ ([a-z][a-z0-9-]*/v\d+)", text))


RETIRED_NOTE = re.compile(r"\bread, (?:never written|normalised in)\b")


def _claimed_retired(rows):
    """The ids Part 32's opening block says it no longer writes.

    Two shapes, because a line states it two ways: a note that is
    wholly a retirement note claims every id on the line, and a note
    that names ids beside the marker claims exactly those. `UX-659`
    needs both - the block may either move a retired id to a `read,
    never written` line or distinguish it in place, and the property
    is what the block claims, not where a name sits.
    """
    claimed = set()
    for ids, annotation in rows:
        if not RETIRED_NOTE.search(annotation):
            continue
        named = set(re.findall(r"[a-z][a-z0-9-]*/v\d+", annotation))
        claimed |= (named & set(ids)) or set(ids)
    return claimed


def _cited_item(annotation):
    """The task file the annotation cites, or `None`."""
    found = re.search(r"UX-(\d+)", annotation)
    if not found:
        return None
    files = sorted(BACKLOG.glob(f"UX-{int(found.group(1)):04d}-*.md"))
    return files[0] if files else None


class TestPart32sOpeningBlockIsTheRegistry:
    """`UX-651`. The registry has two copies and only one was read.

    `UX-565` pointed `test_every_published_schema_is_named_in_the_spec`
    at 32.5's table, because "mentioned anywhere in Part 32" let a
    deleted 32.5 row pass - and nothing then read the block. Measured
    when this was filed: `analyze/v5` (`UX-641`) and
    `capacity-model/v1` (`UX-613`) were in `contracts.ids()`, in 32.5
    and in the architecture inventory, and in no line of the block; its
    retired line still cited `UX-535` for a set now beginning at
    `analyze/v5`. The whole file was green.
    """

    def test_every_id_the_package_has_reaches_the_block(self):
        """The item's Acceptance Test: a contract added to the package
        and not to the block fails here, by name."""
        from bga import contracts

        named = {one for ids, _ in _part_32_opening_block() for one in ids}
        missing = sorted(set(contracts.ids()) - named)
        assert missing == [], (
            f"id(s) Part 32's opening block does not name: {missing}. It is "
            f"the first thing a reader of the spec meets, and 32.5's table "
            f"being right does not make it right (UX-651)")

    def test_the_block_names_nothing_the_package_does_not_have(self):
        """The other direction, and the reason it is three sets rather
        than one: the block opens with the *inputs*, which `ids()` has
        never held (`UX-540`), and with `analysis/v9`, which is stamped
        on nothing and reaches a consumer only as `analyze/v6`. Both
        are read off the package and off Part 32's own subsections, so
        a stale id has nowhere to hide behind them."""
        from bga import contracts

        known = (set(contracts.ids()) | set(contracts.reads())
                 | _part_32_subsections())
        named = {one for ids, _ in _part_32_opening_block() for one in ids}
        stale = sorted(named - known)
        assert stale == [], (
            f"Part 32's opening block names id(s) nothing emits, reads or "
            f"gives a subsection to: {stale}")

    def test_a_retired_line_holds_retired_ids_only(self):
        """`superseded()` is what a release still opens after retiring
        it, and a live id on one of those lines says the tool stopped
        writing something it writes every run."""
        from bga import contracts

        superseded = set(contracts.superseded())
        wrong = sorted(one for ids, annotation in _part_32_opening_block()
                       if annotation.startswith("read")
                       for one in ids if one not in superseded)
        assert wrong == [], (
            f"Part 32's read-never-written lines name id(s) that are not in "
            f"contracts.superseded(): {wrong}")

    def test_every_superseded_id_sits_on_a_line_that_says_it_is_retired(self):
        """`UX-659`. The clause above is keyed on the lines that claim
        to be retired, so a retired id on a line claiming nothing is
        outside its population by construction: `plane2/v2` and
        `plane2/v1` sat beside the live `plane2/v3` under `the Plane 2
        report`, and the whole class was green.

        This runs over `contracts.superseded()` instead - a population
        the block cannot shrink - so the block has to state liveness
        for every retired id, wherever it puts it. No intersection with
        the ids the block names: all ten are in `contracts.ids()`, and
        an id missing from the block entirely is also not claimed.
        """
        from bga import contracts

        claimed = _claimed_retired(_part_32_opening_block())
        unclaimed = sorted(set(contracts.superseded()) - claimed)
        assert unclaimed == [], (
            f"Part 32's opening block does not say that these id(s) of "
            f"contracts.superseded() are no longer written: {unclaimed}. A "
            f"reader asking which member of the family bga writes is given "
            f"the names and no distinction (UX-659)")

    def test_a_retired_line_cites_the_item_that_retired_it(self):
        """Its newest id first, and beside it the item that moved off
        that id - which is the item naming both it and the live id of
        the same family that replaced it.

        Naming the retired id alone does not discriminate and was
        measured not to: the line cited `UX-535` for a set beginning at
        `analyze/v5`, and `UX-535` names `analyze/v5` too - it is what
        *created* it, one bump before `UX-641` retired it. Only the
        retiring item also names the successor.
        """
        from bga import contracts

        live = set(contracts.ids()) - set(contracts.superseded())
        for ids, annotation in _part_32_opening_block():
            if not annotation.startswith("read"):
                continue
            item = _cited_item(annotation)
            assert item is not None, (
                f"the retired line `{ids[0]} ... ({annotation})` cites no "
                f"item, so a reader cannot find what retired it")
            body = item.read_text(encoding="utf-8")
            assert ids[0] in body, (
                f"{item.name} does not name {ids[0]}, the newest id on the "
                f"line it is cited from")
            family = ids[0].split("/")[0] + "/"
            replacements = sorted(one for one in live if one.startswith(family))
            if not replacements:
                continue
            assert [one for one in replacements if one in body], (
                f"{item.name} names {ids[0]} but none of {replacements} - it "
                f"is the item that *created* {ids[0]}, not the one that "
                f"retired it, so the annotation is a bump behind (UX-651)")

    def test_the_block_is_what_part_32_opens_with(self):
        """Non-vacuity for the two directions above, which are set
        differences and pass on an empty parse. The anchor is a heading
        and a fence, and both move."""
        from bga import contracts

        rows = _part_32_opening_block()
        named = {one for ids, _ in rows for one in ids}
        assert len(named) >= len(contracts.ids()), (
            f"the block parse found {len(named)} id(s) against "
            f"{len(contracts.ids())} in the package - the fence or the "
            f"heading moved and the clauses above are reading nothing")
        assert all(annotation for _, annotation in rows), (
            "a block line carries no annotation saying what its group is")
        after = SPEC.read_text(encoding="utf-8")[
            SPEC.read_text(encoding="utf-8").index(PART_32):]
        assert after.index("```text") < after.index("\n## 32.1 "), (
            "Part 32's first fenced block is not above 32.1, so the parse "
            "above is reading some other block")




def _row_keys(node, found):
    """Every key of every row `node` hands a consumer, at any depth.

    Two declarations, because a row has two: an array's `items`, and
    the `bga:columns` an array node carries. `UX-655` measured why both
    are needed - `analyze/v6`'s `parallelism.levels` has no `type` and
    no `items` at all, so its columns are the only statement of what a
    row of it holds, and `level` and `width` are in no `items` anywhere.
    """
    if isinstance(node, dict):
        items = node.get("items")
        if isinstance(items, dict):
            found |= set(items.get("properties", {}))
        for column in node.get("bga:columns") or ():
            if isinstance(column, dict) and isinstance(column.get("key"), str):
                found.add(column["key"])
        for value in node.values():
            _row_keys(value, found)
    elif isinstance(node, list):
        for value in node:
            _row_keys(value, found)
    return found


def _consumer_surface():
    """`{key: [contract, ...]}` - the keys a consumer of a printable
    document meets.

    Each schema's top-level properties, plus every row it hands over at
    any depth: a row of `store/v1`'s `snapshots` is what a reader
    actually holds, and `queue_wait_us` lives only there. Depth is
    `UX-655`: `parallelism` is a top-level *object* and its `levels`
    rows one level below that, so a walk stopping under a top-level
    array published `level` and `width` outside its own population.

    Still not the full recursive key set - 514 distinct keys over the
    nine printable schemas, 891 counting repeats - most of them
    internal shapes of one block, and a document naming all of them
    would be the second copy of the schemas `UX-384` already banned
    from the inventory. This walk is 236.
    """
    from bga import contracts, schemas

    found = {}
    for name in contracts.printable():
        schema = schemas.schema(name)
        keys = set(schema.get("properties", {}))
        _row_keys(schema, keys)
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


def _coverage_section():
    """The body of the guide's coverage section, and only that.

    The subject is the section, not the file: `UX-628` measured a
    clause over the whole guide that could not fail, because line 345
    names the three input contracts while describing what `bga analyze`
    reads.
    """
    section = CLI_GUIDE.read_text(encoding="utf-8").split(
        "### Which keys the prose names", 1)
    assert len(section) == 2, (
        "docs/guides/cli.md has no `### Which keys the prose names` section")
    return section[1].split("\n## ", 1)[0].split("\n### ", 1)[0]


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
    for all of them would have been red on arrival and silenced, so
    `UX-628` shipped a ratchet and `UX-636` walked it to zero. The six
    clauses below are what stopped the ratchet being an off switch and
    now hold the statement it became.
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
            f"this was written and 236 once UX-655 gave it depth, so either "
            f"a contract stopped resolving or the walk above stopped "
            f"descending")
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

    def test_the_register_is_empty(self):
        """`UX-636`: the ratchet reached zero and is a statement now.
        80 when `UX-628` froze it, 0 once the guide's key reference
        landed - and an entry back in it is a debt somebody argues for,
        not a number that drifts. Whether an *undocumented* key is in
        the register is the clause above, asserted there and not
        restated here - one mutation that reddens two clauses has
        falsified one."""
        assert UNDOCUMENTED_WHEN_THE_POPULATION_BECAME_KEYS == frozenset(), (
            f"the register holds "
            f"{sorted(UNDOCUMENTED_WHEN_THE_POPULATION_BECAME_KEYS)}; it was "
            f"emptied by UX-636 and a key with no prose reddens the clause "
            f"above by name rather than being excused here")

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

    def test_the_surface_reaches_a_row_below_a_top_level_object(self):
        """`UX-655`. `parallelism` is a top-level object and its
        `levels` rows are one level below that, so a population
        stopping under a top-level array published the whole of a major
        bump - `level`, `width`, `elements` for the integers they
        replaced - outside itself, with the register at zero and every
        clause green.

        The row's keys are read off the row rather than restated, so
        the fourth column this item's Acceptance Test adds is in the
        population by existing.
        """
        from bga import schemas

        row = schemas.schema("analyze/v6")["properties"]["parallelism"][
            "properties"]["levels"]
        declared = [column["key"] for column in row["bga:columns"]]
        assert declared, "parallelism.levels declares no columns to reach"
        surface = _consumer_surface()
        missing = [key for key in declared
                   if "analyze/v6" not in surface.get(key, ())]
        assert missing == [], (
            f"key(s) of an analyze/v6 row the consumer surface does not "
            f"reach: {missing}. A consumer indexing parallelism.levels reads "
            f"exactly these, so a key of one going undocumented is invisible "
            f"to every clause above (UX-655)")

    def test_a_row_can_be_declared_by_its_columns_alone(self):
        """Why the walk reads `bga:columns` and not `items` only, and
        it is asserted rather than assumed because it is a property of
        a schema somebody else maintains. `parallelism.levels` carries
        no `type` and no `items`: its columns are the whole declaration
        of what a row of it holds. Give it an `items` and this fails,
        and reading columns is re-decided rather than inherited."""
        from bga import schemas

        row = schemas.schema("analyze/v6")["properties"]["parallelism"][
            "properties"]["levels"]
        assert "items" not in row and "type" not in row, (
            "parallelism.levels declares items or a type now, so bga:columns "
            "is no longer the only thing that reaches its row")
        def items_only(node, found):
            """The walk without the columns half - `UX-655` measured it
            at 218 keys, holding neither of the two below."""
            if isinstance(node, dict):
                items = node.get("items")
                if isinstance(items, dict):
                    found |= set(items.get("properties", {}))
                for value in node.values():
                    items_only(value, found)
            elif isinstance(node, list):
                for value in node:
                    items_only(value, found)
            return found

        assert {"level", "width"}.isdisjoint(
            items_only(schemas.schema("analyze/v6"), set())), (
            "an items-only walk reaches level or width, so reading "
            "bga:columns is not what carries this row and the clause above "
            "would pass without it")

    def test_the_guide_states_the_reach_it_actually_has(self):
        """The other half of the Required Fix. The statement was
        unqualified while the population stopped one level down, so a
        bump whose whole content landed deeper read as covered. The
        figure is derived off the walk, so widening or narrowing it
        moves the guide rather than leaving a stale number."""
        body = _coverage_section()
        surface = _consumer_surface()
        assert f"**{len(surface)} keys**" in body, (
            f"the coverage section does not state the {len(surface)} keys "
            f"the walk reaches; a reader cannot tell how far it goes from a "
            f"figure that is not there")
        for stated in ("bga:columns", "any depth"):
            assert stated in body, (
                f"the coverage section does not say `{stated}` - the two "
                f"things that decide what counts as a row, and the depth "
                f"they are looked for at, are what the statement is about")

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
