"""UX-1292: every sentence counting the viewer's canned questions says the library's count.

The count is `QUESTIONS` in `bga/viewer/questions.js`, never
`bga.provenance.TRACE_QUERIES`, whose keys are the claims pointing at a
question (24 claims onto 18 questions on this guard's base).
"""

import json
import pathlib
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
NODE = shutil.which("node")

WORDS = {
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
    21: "twenty-one",
    22: "twenty-two",
}

#: (document, the sentence with `{n}` where the count goes), whitespace-collapsed
SENTENCES = (
    ("README.md", "sorts all {n} canned questions"),
    ("docs/guides/what-the-viewer-answers.md", "serves {n} questions"),
    ("docs/guides/what-the-viewer-answers.md", "of the {n} questions"),
)


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_every_sentence_counts_the_library_the_page_serves():
    script = 'const { QUESTIONS } = await import("./bga/viewer/questions.js"); console.log(JSON.stringify(QUESTIONS.map((q) => q.id)));'
    done = subprocess.run(
        [NODE, "--input-type=module", "-e", script], capture_output=True, text=True, cwd=REPO, timeout=60
    )
    assert done.returncode == 0, done.stderr
    served = json.loads(done.stdout)
    assert len(served) == len(set(served)) and len(served) >= 10, served
    assert len(served) in WORDS, f"{len(served)} questions, and this guard has no word for it - add one"
    word = WORDS[len(served)]
    wrong = [
        f"{doc}: wants {sentence.format(n=word)!r}"
        for doc, sentence in SENTENCES
        if sentence.format(n=word) not in " ".join((REPO / doc).read_text(encoding="utf-8").split())
    ]
    assert wrong == [], f"the page serves {len(served)} questions and these sentences do not say so:\n  " + "\n  ".join(
        wrong
    )
