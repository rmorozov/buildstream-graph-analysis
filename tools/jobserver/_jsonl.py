"""UX-901: one tolerant JSON-lines read for every ledger reader here."""
import json
from typing import Optional


def jsonl_rows(path: Optional[str]) -> list:
    """Each parsed line of `path`; blank and malformed lines skipped, `[]`
    when the path is absent or unreadable - an interrupted capture's
    truncated last line is the case this tolerates."""
    if not path:
        return []
    rows = []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        return []
    return rows
