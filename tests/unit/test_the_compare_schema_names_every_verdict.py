"""`compare/v2`'s description and the guides name every verdict `compare.py` emits (UX-1333)."""

from pathlib import Path

from bga import schemas
from bga.compare import VERDICT_SENTENCES

GUIDES = Path(__file__).resolve().parents[2] / "docs" / "guides"


def _labels() -> list[str]:
    return list(VERDICT_SENTENCES.values())


def test_the_schema_description_names_every_label():
    description = schemas._SCHEMAS["compare/v2"]()["description"]
    assert [label for label in _labels() if f"`{label}`" not in description] == []


def test_cli_guide_verdict_sentence_names_every_label():
    text = (GUIDES / "cli.md").read_text()
    start = text.index("The verdict is one of")
    sentence = text[start : text.index("\n", start)]
    assert [label for label in _labels() if label not in sentence] == []


def test_the_contract_and_comment_guides_name_every_label():
    for guide in ("json-contracts.md", "ci-comment.md"):
        text = (GUIDES / guide).read_text()
        assert [label for label in _labels() if label not in text] == [], guide
