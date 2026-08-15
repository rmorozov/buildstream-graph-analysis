#!/usr/bin/env bash
# Regenerates the throwaway git "upstream" that
# examples/03-project-refs-identity's libbar.bst git source points at,
# deterministically (fixed committer identity and dates) into
# examples/03-project-refs-identity/.generated-remote/ - gitignored,
# never committed, same "generate non-source content at build time"
# pattern as stage_runtimes.sh. Determinism means the resulting commit
# SHA is reproducible from the committed remote-seed*/ content alone, not
# tied to when/where this script runs.
#
# Usage:
#   stage_project3_remote.sh          # first commit only (remote-seed/)
#   stage_project3_remote.sh --update # also apply the second commit
#                                      # (remote-seed-v2/), for the
#                                      # "touch and rebuild" retry-data run
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$HERE/03-project-refs-identity"
REMOTE_DIR="$PROJECT_DIR/.generated-remote"

export GIT_AUTHOR_NAME="bga-example"
export GIT_AUTHOR_EMAIL="bga-example@example.invalid"
export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"

rm -rf "$REMOTE_DIR"
mkdir -p "$REMOTE_DIR"
git -C "$REMOTE_DIR" init -q -b main
cp "$PROJECT_DIR/remote-seed/"* "$REMOTE_DIR/"
git -C "$REMOTE_DIR" add -A
GIT_AUTHOR_DATE="2020-01-01T00:00:00Z" GIT_COMMITTER_DATE="2020-01-01T00:00:00Z" \
    git -C "$REMOTE_DIR" commit -q -m "seed v1"

if [ "${1:-}" = "--update" ]; then
    cp "$PROJECT_DIR/remote-seed-v2/"* "$REMOTE_DIR/"
    git -C "$REMOTE_DIR" add -A
    GIT_AUTHOR_DATE="2020-01-02T00:00:00Z" GIT_COMMITTER_DATE="2020-01-02T00:00:00Z" \
        git -C "$REMOTE_DIR" commit -q -m "update v2"
fi

# libbar.bst.in -> libbar.bst: BuildStream project options have no
# free-form string type (confirmed via a real CI failure), so the
# per-checkout absolute remote path is substituted directly into the
# element file instead - gitignored, regenerated here every time.
sed "s|@REMOTE_PATH@|$REMOTE_DIR|g" \
    "$PROJECT_DIR/elements/libbar.bst.in" > "$PROJECT_DIR/elements/libbar.bst"

echo "Generated remote at $REMOTE_DIR (HEAD $(git -C "$REMOTE_DIR" rev-parse HEAD))"
