#!/usr/bin/env bash
# Local development convenience script (P4-04-adjacent, P4-03): one
# command from "I changed some code" to "I can see what a real report
# looks like."
#
# Reuses the checked-in tests/fixtures/golden/mixed_task_kinds/ fixture
# (P3-08) - small, static, always ready, no regeneration needed - rather
# than inventing a third fixture. Pass --large to use the bigger, more
# realistic tests/fixtures/synthetic_multi_subproject/ fixture instead
# (regenerated fresh via its own generate_fixture.py so it always
# reflects the current build_model.py).
#
# Not a substitute for `make test`/pytest - this is a fast, narrow "does
# the tool still basically work and what does it show me" smoke-check
# loop.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FIXTURE_DIR="tests/fixtures/golden/mixed_task_kinds"
LABEL="small (golden/mixed_task_kinds)"

if [[ "${1:-}" == "--large" ]]; then
    LABEL="large (synthetic_multi_subproject)"
    TMP_DIR="$(mktemp -d)"
    trap 'rm -rf "$TMP_DIR"' EXIT
    PYTHONPATH=. python3 -c "
from pathlib import Path
from tests.fixtures.synthetic_multi_subproject.generate_fixture import write_fixture
write_fixture(Path('$TMP_DIR'))
"
    FIXTURE_DIR="$TMP_DIR"
fi

echo "bga dev run - using $LABEL fixture: $FIXTURE_DIR" >&2
echo "============================================================" >&2

PYTHONPATH=. python3 -m bga.cli analyze "$FIXTURE_DIR" --diagnostics
