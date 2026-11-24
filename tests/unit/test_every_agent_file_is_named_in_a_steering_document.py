"""UX-1381: an agent under `.claude/agents/` that neither `CLAUDE.md` nor the fixing guide names is one a session cannot find."""

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
AGENTS = REPO / ".claude/agents"
DOCUMENTS = [REPO / "CLAUDE.md", REPO / "docs/contributing/fixing-guide.md"]


def test_every_agent_file_is_named_in_claude_md_or_the_fixing_guide():
    text = "\n".join(d.read_text(encoding="utf-8") for d in DOCUMENTS)
    agents = sorted(p.stem for p in AGENTS.glob("*.md"))
    assert agents, "no agent files found"
    missing = [a for a in agents if not re.search(rf"(?<![\w-]){re.escape(a)}(?![\w-])", text)]
    assert missing == [], (
        f"agent(s) {missing} under .claude/agents/ are named in neither CLAUDE.md nor the fixing guide"
    )
