#!/usr/bin/env bash
# Populates every examples/*/files/runtime/bin/ with a real shell (and
# common utilities) for that project's manual.bst elements to run
# commands with. BuildStream's sandbox is assembled purely from staged
# dependencies - nothing from the host is bound in - so something has to
# actually provide /bin/sh; this stages a static busybox (installed via
# the `busybox-static` package) rather than committing a binary to the
# repo. Not needed for `bst show`/graph-only work, only for a real `bst
# build`. See examples/README.md.
set -euo pipefail

BB="$(command -v busybox)"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for project_dir in "$HERE"/*/; do
    bin_dir="${project_dir}files/runtime/bin"
    [ -d "$bin_dir" ] || continue
    for applet in sh sleep true env cat; do
        cp "$BB" "${bin_dir}/${applet}"
    done
done
