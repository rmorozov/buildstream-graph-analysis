"""UX-898/UX-903: what the build was, beside what machine ran it.

`hostinfo` answers "same machine?". Nothing answered "same build?" - a
nightly and a review build of one project differ in targets, cache
state and often agent, and a sanitizer build's elements are slower by a
factor that belongs to the sanitizer. Pooled, they produce a median
that describes no build anyone runs.

Two declared axes, because they are different questions: the **type**
says when and why a build ran (`night`, `review`, `guard`), the
**variant** says what it did (`arch=aarch64`, `sanitizer=address`).
Several variant dimensions are true at once, so the variant is a map
rather than a string - the owner's matrix is per instruction set *and*
release-with-symbols *and* coverage.

Free text both, declared by the pipeline rather than enumerated here:
no enum this repository maintains fits a pipeline nobody has seen. The
cost is that a typo makes a third class rather than an error, which is
why every refusal prints both values it saw.

Comparison is exact and case-sensitive. `Nightly` and `nightly` are two
declarations, not one: folding case would be `bga` deciding that a
pipeline's two spellings mean one thing, which is a guess, and this
module refuses rather than guesses.

Not a contract id of its own: two declared fields inside
`run-context/v9`, a permitted addition under the spec's versioning rule.
"""
from typing import Optional

# The keys a difference in which makes two runs a different class. The
# pair, not either half: a nightly sanitizer build and a review
# sanitizer build share a variant and are not the same population.
COMPARED_FIELDS = ("type", "variant")

_FIELD_LABELS = {"type": "build type", "variant": "variant"}

# What a declared-but-empty half reads as in a refusal. Distinct from
# "not declared at all", which is `absent` below and never refuses.
NOT_DECLARED = "(not declared)"


def declare(build_type: Optional[str] = None,
            variant: Optional[dict] = None) -> Optional[dict]:
    """The block a capture records, or `None` when nothing was declared.

    Whitespace is stripped because a trailing space in a CI variable is
    a declaration accident and not a second build type; case is not
    touched, for the reason in the module docstring.
    """
    kind = (build_type or "").strip() or None
    dimensions = {
        str(name).strip(): str(value).strip()
        for name, value in (variant or {}).items()
        if str(name).strip()
    }
    if kind is None and not dimensions:
        return None
    return {"type": kind, "variant": dimensions}


def parse_variant(pairs) -> dict:
    """`["arch=aarch64", "sanitizer=address"]` as a dimension map.

    Raises `ValueError` naming the entry: a `--variant` with no `=` is
    a dimension whose name `bga` would have to invent, and inventing
    one is how `asan` and `sanitizer=asan` become two classes.
    """
    dimensions = {}
    for pair in pairs or []:
        name, sep, value = str(pair).partition("=")
        if not sep or not name.strip():
            raise ValueError(
                f"--variant wants name=value, got {pair!r}. A variant is a "
                f"named dimension (arch, sanitizer, coverage) so that two "
                f"of them can be true at once.")
        dimensions[name.strip()] = value.strip()
    return dimensions


def parse_variant_env(text: Optional[str]) -> dict:
    """`BGA_BUILD_VARIANT="arch=aarch64,sanitizer=address"`.

    Comma-separated because a CI variable is one string; the same
    `name=value` rule, so the two declaration paths cannot disagree.
    """
    entries = [part for part in (text or "").split(",") if part.strip()]
    return parse_variant(entries)


def _variant_of(block: Optional[dict]) -> dict:
    return dict((block or {}).get("variant") or {})


def differing_fields(baseline: Optional[dict],
                     candidate: Optional[dict]) -> list[str]:
    """Which of `COMPARED_FIELDS` two declared blocks disagree on.

    Both blocks declared, or this is not the question - an undeclared
    side is `classify`'s `unknown`, never a difference, because the
    absence is not evidence of a mismatch either.
    """
    if not baseline or not candidate:
        return []
    differing = []
    if baseline.get("type") != candidate.get("type"):
        differing.append("type")
    if _variant_of(baseline) != _variant_of(candidate):
        differing.append("variant")
    return differing


def differing_dimensions(baseline: Optional[dict],
                         candidate: Optional[dict]) -> list[str]:
    """The variant dimension names the two disagree on, sorted."""
    before, after = _variant_of(baseline), _variant_of(candidate)
    return sorted(name for name in set(before) | set(after)
                  if before.get(name) != after.get(name))


def classify(baseline: Optional[dict], candidate: Optional[dict]) -> dict:
    """`{"status": same|different|unknown|absent, "differing": [...]}`.

    `absent` - neither run declared - is the whole history of this
    repository before `UX-898`, so it renders nothing and refuses
    nothing: every capture taken before the row compares exactly as it
    did. `unknown` is one side declaring: a caveat, not a refusal, the
    same call `hostinfo.classify` makes for a run older than its
    manifest.
    """
    if not baseline and not candidate:
        return {"status": "absent", "differing": [], "missing": []}
    if not baseline or not candidate:
        missing = []
        if not baseline:
            missing.append("baseline")
        if not candidate:
            missing.append("candidate")
        return {"status": "unknown", "differing": [], "missing": missing}
    differing = differing_fields(baseline, candidate)
    return {
        "status": "different" if differing else "same",
        "differing": differing,
        "missing": [],
    }


def _value_clause(field: str, baseline: Optional[dict],
                  candidate: Optional[dict]) -> str:
    """One `label: a vs b` clause, naming both values it saw."""
    label = _FIELD_LABELS.get(field, field)
    if field == "variant":
        before, after = _variant_of(baseline), _variant_of(candidate)
        parts = [f"{name}={before.get(name, NOT_DECLARED)} vs "
                 f"{after.get(name, NOT_DECLARED)}"
                 for name in differing_dimensions(baseline, candidate)]
        return f"{label}: " + "; ".join(parts or [NOT_DECLARED])
    before = (baseline or {}).get(field) or NOT_DECLARED
    after = (candidate or {}).get(field) or NOT_DECLARED
    return f"{label}: {before} vs {after}"


def describe(classification: dict,
             baseline: Optional[dict],
             candidate: Optional[dict]) -> Optional[str]:
    """One sentence for the report, or `None` when there is nothing to say.

    Names the values on both sides, because a free-text declaration's
    one failure mode is a typo and "different build type" is a sentence
    a reader cannot act on.
    """
    status = classification.get("status")
    if status in ("same", "absent"):
        return None
    if status == "unknown":
        missing = " and ".join(classification.get("missing") or ["one run"])
        declared = baseline or candidate
        return (f"Build class unknown: the {missing} declares none, while the "
                f"other is {label(declared)}. A build type and variant are "
                f"declared at capture time, so an undeclared run cannot say "
                f"whether it built the same thing.")
    clauses = "; ".join(
        _value_clause(field, baseline, candidate)
        for field in classification.get("differing") or [])
    return (f"Mixed build class: these runs declare different builds "
            f"({clauses}). A build type says when and why a build ran and a "
            f"variant says what it did, so the difference between the two "
            f"runs is not evidence about the change.")


def label(block: Optional[dict]) -> Optional[str]:
    """`review · arch=aarch64 · sanitizer=address`, or `None`.

    Human-readable rather than a hash, because it ends up in a refusal
    sentence and in the report header a reader has to act on. Variant
    dimensions sorted, so one declaration has one label.
    """
    if not block:
        return None
    parts = []
    if block.get("type"):
        parts.append(str(block["type"]))
    parts.extend(f"{name}={value}"
                 for name, value in sorted(_variant_of(block).items()))
    return " · ".join(parts) or None


def homogeneous(blocks: list[Optional[dict]]) -> bool:
    """Whether every declared block in a set names one build.

    Undeclared blocks are skipped rather than counted as a mismatch -
    the same rule `differing_fields` applies to a pair.
    """
    declared = [block for block in blocks if block]
    if len(declared) < 2:
        return True
    first = declared[0]
    return all(not differing_fields(first, other) for other in declared[1:])
