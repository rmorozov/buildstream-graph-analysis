# UX-846: sourced by every wrapper in this directory - "a tool that
# will not read the pipe holds tokens instead". `bga_run_wrapped
# <threads|dashj> "$@"` is the one entry point: find the real tool past
# this directory on PATH, read MAKEFLAGS for a jobserver auth, acquire
# up to $BST_TRACE_WRAPPER_CAP tokens non-blockingly (bounded 50ms),
# run the tool with that width plus its own implicit token, and return
# exactly the tokens read - via a trap, so a killed *child* still
# leaves the wrapper (the parent, running the tool as a foreground job
# rather than exec'ing into it) to give them back. A wrapper killed
# itself leaks until UX-852's audit.

# UX-918: parameter expansion, not `dirname`/`basename` - a sandbox
# staged by `examples/stage_cpp_toolchain.sh` has no coreutils, and this
# line runs at source time under `set -eu`, so an absent `dirname` failed
# the build before any wrapper logic ran (bst-examples exit 255).
bga_dir0=${0%/*}
if [ "$bga_dir0" = "$0" ]; then bga_dir0=.; fi
bga_self_dir=$(CDPATH= cd -- "$bga_dir0" && pwd)
bga_tool=${0##*/}
bga_held=0
bga_wfd=

# UX-846 (post-merge incident): `$0`'s directory is the *invoked* path's
# directory, not necessarily the wrapper directory on `PATH` - a symlink,
# a relative path, or a copy elsewhere all break that assumption. Without
# this, `bga_find_real` picked the wrapper itself back up as "real",
# `"$real" --help` re-entered it, and the loop had no bound: 32,000
# processes, a container restart. `bga_resolve` follows symlinks with
# `readlink -f` where it exists; a candidate is also skipped if its own
# first 3 lines carry this item's own marker (a copy, not a symlink).
bga_resolve() {
    readlink -f -- "$1" 2>/dev/null || printf '%s\n' "$1"
}

# UX-918: the marker scan, in the shell - `head -3 | grep` needs two
# binaries a staged sandbox has not got, and a pipeline that dies 127
# reads as "no marker", which silently disarms UX-846's recursion guard.
bga_marks_self() {
    [ -r "$1" ] || return 1
    bga_seen=0
    while [ "$bga_seen" -lt 3 ] && IFS= read -r bga_line; do
        bga_seen=$((bga_seen + 1))
        case $bga_line in *UX-846*) return 0 ;; esac
    done < "$1"
    return 1
}

bga_find_real() {
    self_resolved=$(bga_resolve "$0")
    old_ifs=$IFS
    IFS=:
    set -- $PATH
    IFS=$old_ifs
    for dir in "$@"; do
        [ -n "$dir" ] || continue
        [ "$dir" = "$bga_self_dir" ] && continue
        candidate="$dir/$bga_tool"
        [ -x "$candidate" ] || continue
        [ "$(bga_resolve "$candidate")" = "$self_resolved" ] && continue
        bga_marks_self "$candidate" && continue
        printf '%s\n' "$candidate"
        return 0
    done
    return 1
}

bga_ledger() {
    [ -n "${BST_TRACE_JOBSERVER_LEDGER:-}" ] || return 0
    printf '{"event":"%s","tool":"%s","pid":%s,"tokens":%s,"t":%s}\n' \
        "$1" "$bga_tool" "$$" "$bga_held" "$(date +%s.%N 2>/dev/null || echo 0)" \
        >>"$BST_TRACE_JOBSERVER_LEDGER" 2>/dev/null || :
}

bga_release() {
    i=0
    while [ "$i" -lt "$bga_held" ]; do
        printf '+' >&"${bga_wfd:-9}" 2>/dev/null || :
        i=$((i + 1))
    done
    bga_ledger release
}

# UX-880: the GCC-driver LTO shim - a grandchild across bwrap cannot
# open the raw fd `--jobserver-auth` names, so this strips it from the
# MAKEFLAGS it hands the real compiler unconditionally, and only when
# `-flto` is already requested, pins it to a static `-flto=N` cap
# lto-wrapper can honour without a jobserver. A non-LTO invocation's
# argv is untouched - this must never *introduce* LTO.
#
# UX-880 (verifier fix): these scripts sit in the one shared wrapper
# directory every jobserver-active sandbox mounts (UX-846), so they are
# on `PATH` whether or not *this* element's own override resolved to
# `flto` - gated on `BST_TRACE_FLTO_ACTIVE=1`, set only by
# `_jobserver_injection` for a matched element, never re-derived here.
# Unset (or anything but `1`): pure pass-through, argv and MAKEFLAGS
# both untouched - a working dynamic-fifo build must not be silently
# pinned to a static cap just because this shim happens to be on PATH.
bga_run_flto() {
    real=$1
    shift

    if [ "${BST_TRACE_FLTO_ACTIVE:-}" != "1" ]; then
        exec "$real" "$@"
    fi

    stripped=
    for flag in ${MAKEFLAGS:-}; do
        case "$flag" in
            --jobserver-auth=*) ;;
            *) stripped="$stripped $flag" ;;
        esac
    done
    export MAKEFLAGS=${stripped# }

    has_flto=0
    for arg in "$@"; do
        case "$arg" in
            -flto | -flto=jobserver | -flto=auto) has_flto=1 ;;
        esac
    done
    if [ "$has_flto" -eq 0 ]; then
        exec "$real" "$@"
    fi

    cap=${BST_TRACE_LTO_CAP:-$(nproc 2>/dev/null || echo 1)}
    n=$#
    i=0
    while [ "$i" -lt "$n" ]; do
        i=$((i + 1))
        arg=$1
        shift
        case "$arg" in
            -flto | -flto=jobserver | -flto=auto) arg="-flto=$cap" ;;
        esac
        set -- "$@" "$arg"
    done
    exec "$real" "$@"
}

# `flag_style` is `threads` (--threads=N), `dashj` (-j N) or `flto`
# (UX-880 - not a token-holder at all, see `bga_run_flto` above).
bga_run_wrapped() {
    flag_style=$1
    shift

    # UX-846 (post-merge incident): the last line, independent of
    # whatever `bga_find_real` above concludes - if this process is
    # already inside a wrapper invocation for the *same* tool name, it
    # is a repeat by construction and must never recurse again,
    # regardless of the cause. Exported before `bga_find_real` or
    # `--help` ever run, so every process in the chain carries it.
    if [ "${BGA_WRAPPER_TOOL:-}" = "$bga_tool" ]; then
        echo "bga: $bga_tool: wrapper re-entered itself" >&2
        exit 127
    fi
    export BGA_WRAPPER_TOOL="$bga_tool"

    real=$(bga_find_real) || {
        echo "bga: $bga_tool: no real tool found on PATH past $bga_self_dir" >&2
        exit 127
    }

    if [ "$flag_style" = "flto" ]; then
        bga_run_flto "$real" "$@"
    fi

    auth=
    for flag in ${MAKEFLAGS:-}; do
        case "$flag" in
            --jobserver-auth=*) auth=${flag#--jobserver-auth=} ;;
        esac
    done

    if [ -z "$auth" ]; then
        exec "$real" "$@"
    fi

    # UX-846: the same fact the capture's pass-through policy probed
    # before the build, checked again here - belt and braces against a
    # tool that ended up on this PATH despite speaking the protocol.
    if "$real" --help 2>&1 | grep -qi jobserver; then
        exec "$real" "$@"
    fi

    # A redirection failure here is fatal to a POSIX `exec` (no command)
    # rather than something `||` can catch - accepted, since a jobserver
    # auth string this wrapper cannot open is already a broken build.
    #
    # `/dev/fd/$r`, not `exec 9<&"$r"`: dash's IO-number lexer only
    # recognises a *single*-digit fd immediately before `<&`/`>&` -
    # `exec 9<&"$r"` with a real two-digit inherited fd (11, common
    # once bwrap and the trace hook have their own open) fails outright
    # with "Bad fd number", silently discarding the whole pool. A path
    # under `/dev/fd/` is an ordinary filename argument to the parser,
    # so the digit-count limit never applies (measured: `exec
    # 15<>/dev/null` fails the same way `dash` here; `exec
    # 9<>/dev/fd/15` does not).
    case "$auth" in
        fifo:*)
            fifo_path=${auth#fifo:}
            exec 9<>"$fifo_path"
            bga_wfd=9
            ;;
        *)
            r=${auth%%,*}
            w=${auth#*,}
            exec 9<>/dev/fd/"$r"
            if [ "$w" != "$r" ]; then
                exec 8>/dev/fd/"$w"
                bga_wfd=8
            else
                bga_wfd=9
            fi
            ;;
    esac

    cap=${BST_TRACE_WRAPPER_CAP:-$(nproc 2>/dev/null || echo 1)}
    # One `dd`, not one fork per token: `count=$cap` non-blocking
    # single-byte reads in dd's own loop, bounded by `timeout` rather
    # than a shell loop polling `date` - measured, the per-fork shell
    # loop this replaced needed 2-3 extra forks per token and missed
    # its own 50ms budget under a loaded machine. `dd` still exits
    # non-zero on a short read (EAGAIN before `count` is reached) -
    # expected, not an error, so `|| :` under `set -e`.
    #
    # `BGA_WRAPPER_ACQUIRE_MS` (default 50): the budget is production's
    # own choice, not a test's - a guard asserting an exact token count
    # must not also be a scheduling bet under `make test`'s own xdist
    # contention. `timeout` takes seconds; `ms / 1000` and `ms % 1000`,
    # zero-padded to 3 digits, is exact for any integer millisecond
    # count (no float parsing, no locale-dependent decimal point).
    acquire_ms=${BGA_WRAPPER_ACQUIRE_MS:-50}
    acquire_budget=$(printf '%d.%03d' "$((acquire_ms / 1000))" "$((acquire_ms % 1000))")
    if command -v timeout >/dev/null 2>&1; then
        out=$(timeout "$acquire_budget" dd bs=1 count="$cap" iflag=nonblock 2>/dev/null <&9) || :
    else
        out=$(dd bs=1 count="$cap" iflag=nonblock 2>/dev/null <&9) || :
    fi
    bga_held=${#out}
    bga_ledger acquire
    trap bga_release EXIT INT TERM HUP

    width=$((bga_held + 1))
    # UX-888: the wrapper owns ninja's -j. Strip the recipe's own
    # -jN/--jobs=N and a lone -j (dropping a following bare-integer arg,
    # but leaving a non-integer - a dangling -j from an emptied `${JOBS}`,
    # e.g. before -C) so the token-held -j<width> below is the only -j
    # ninja sees. POSIX argv rotation: shift from the front, re-append
    # kept args to the back, so args with spaces survive.
    if [ "$flag_style" = dashj ]; then
        n=$#
        i=0
        while [ "$i" -lt "$n" ]; do
            i=$((i + 1))
            arg=$1
            shift
            case "$arg" in
                -j[0-9]* | --jobs=*) continue ;;
                -j)
                    if [ "$i" -lt "$n" ]; then
                        case "$1" in
                            '' | *[!0-9]*) : ;;
                            *) shift; i=$((i + 1)) ;;
                        esac
                    fi
                    continue ;;
            esac
            set -- "$@" "$arg"
        done
    fi
    case "$flag_style" in
        dashj) "$real" -j "$width" "$@" ;;
        *) "$real" "--threads=$width" "$@" ;;
    esac
}
