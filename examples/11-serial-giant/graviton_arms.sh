#!/bin/sh
# UX-905 (`pairs`: off/auto) and UX-895 (`overhead`: none/capture/trace)
# on one quiet host: three interleaved repeats, cold caches every build,
# bst's own `max-jobs` default (min(cpus, 8)). One `::notice::` per arm
# at exit - GitHub keeps ten per step, a line per build would not fit.
set -eu
MODE=$1
PROJ=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-$PWD/arms}
mkdir -p "$OUT/xdg"
export XDG_CONFIG_HOME="$OUT/xdg"
printf 'cache:\n  quota: 20G\n  reserved-disk-space: 2G\n' > "$XDG_CONFIG_HOME/buildstream2.conf"
cd "$PROJ"

summary() {
    for arm in $(cut -d' ' -f1 "$OUT/builds.txt" 2>/dev/null | sort -u); do
        echo "::notice title=$MODE $arm::$(grep "^$arm " "$OUT/builds.txt" | cut -d' ' -f2- | paste -sd';' -)"
    done
}
trap summary EXIT

peak() {
    python3 -c 'import json, sys
r = json.load(open(sys.argv[1]))
print(next((e.get("peak_work_concurrency") for e in r.get("per_element_parallelism") or []
            if e.get("element") == "giant.bst"), "?"))' "$1" 2>/dev/null || echo "?"
}

build() {  # build <arm> <repeat> <plane2 path or -> -- <command...>
    arm=$1 i=$2 plane2=$3; shift 4
    rm -rf ~/.cache/buildstream ~/.local/share/buildstream .bga
    /usr/bin/time -f '%e %U %S' -o "$OUT/time" "$@" > "$OUT/$arm-$i.log" 2>&1 \
        || { tail -40 "$OUT/$arm-$i.log"; exit 1; }
    read -r wall user sys < "$OUT/time"
    [ "$plane2" = - ] || plane2=$(ls $plane2 2>/dev/null | tail -1)
    p=$([ "$plane2" = - ] && echo - || peak "$plane2")
    cpu=$(python3 -c "print(f'{$user + $sys:.0f}')")
    echo "$arm wall ${wall}s cpu ${cpu}s giant-peak $p" | tee -a "$OUT/builds.txt"
}

for i in 1 2 3; do
    case $MODE in
    pairs)
        for m in off auto; do
            build "$m" "$i" "$OUT/$m-$i.json" -- bga capture run --run-dir "$OUT/run-$m-$i" \
                --jobserver "$m" . "$OUT/$m-$i.json" -- bst build all.bst
        done ;;
    overhead)
        build none "$i" - -- bst build all.bst
        build capture "$i" ".bga/runs/*/plane2.json" -- bga snapshot --no-trace-opens -- bst build all.bst
        build trace "$i" ".bga/runs/*/plane2.json" -- bga snapshot --trace-opens -- bst build all.bst ;;
    *) echo "usage: $0 pairs|overhead" >&2; exit 2 ;;
    esac
done
