#!/usr/bin/env bash
# Populates examples/05-cmake-cpp-toolchain/files/toolchain/ with a real,
# working GCC + CMake + GNU Make toolchain. BuildStream's sandbox binds
# in nothing from the host except staged dependencies (same reasoning as
# stage_runtimes.sh's busybox staging, scaled up to a full toolchain) -
# so every binary, shared library, gcc-internal helper and search path
# gcc/cmake hardcode has to be present in the sandbox at the exact same
# absolute path it has where it was built. Nothing here is relocatable,
# so nothing is relocated: this stages a mini sysroot at absolute paths.
#
# Two axes (UX-914). The RUNTIME - glibc, the shell, coreutils - is
# still this host's, copied in at its own /usr paths. The TOOLCHAIN -
# gcc, binutils, cmake - is a pinned nix closure (UX-925/UX-927) staged
# at its own /nix/store/<hash> prefixes with its content-address intact,
# and reached through -B and --sysroot baked into a PATH shim (UX-930),
# since a nix gcc is no more relocatable than Ubuntu's - it simply has a
# prefix this repository can name and check.
#
# See examples/README.md's own `05-cmake-cpp-toolchain` section for how
# to use the result (an earlier revision of this header pointed at a
# `docs/backlog/scenarios/UX-08-...md` and a per-example README.md, neither of
# which was ever written - UX-08 was never filed, see
# docs/backlog/scenarios/README.md).
#
# examples/06-macro-micro-optimization needs the same sysroot in two
# more places (its own files/toolchain and its optimized/ variant's), so
# this script stages once and hardlink-clones into each of them - real
# copies as far as BuildStream is concerned, ~0 extra disk.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HERE/05-cmake-cpp-toolchain/files/toolchain"
rm -rf "$DEST"
mkdir -p "$DEST"

# Real binaries this project's cmake/make elements invoke directly, plus
# the gcc-internal helpers gcc itself execs (cc1/cc1plus/collect2 - found
# via `gcc -print-prog-name=...`, not on $PATH).
#
# UX-914: two axes, declared separately rather than one list, because
# they are blocked on different questions. The RUNTIME decides what a
# recipe's own shell and `make` do - it is where `style_for_make_version`
# reads (UX-874) and where the one pin below lives. The TOOLCHAIN decides
# what the compiled program is; replacing it with a relocatable cross
# toolchain is UX-925, and this split is what lets that happen without
# touching the runtime. tools/sysroot_manifest.py declares which package
# each name comes from and at what version, and verifies it below.
# UX-915: `make` is in neither array - it is pinned, not taken from this
# host. UX-925: neither is anything on the toolchain axis any more -
# gcc, binutils and cmake are one pinned closure, staged below at their
# own /nix/store prefixes, so TOOLCHAIN_BINARIES is empty and the
# axis array stays as the place a *host* toolchain would reappear.
RUNTIME_BINARIES=(
  /usr/bin/env /usr/bin/sh /usr/bin/uname /usr/bin/sort /usr/bin/cat
)
TOOLCHAIN_BINARIES=(
)
BINARIES=( "${RUNTIME_BINARIES[@]}" "${TOOLCHAIN_BINARIES[@]}" )

copy_file_only() {
  local src="$1"
  [ -e "$src" ] || return 0
  local dest="$DEST$src"
  mkdir -p "$(dirname "$dest")"
  cp -a --parents -- "$src" "$DEST" 2>/dev/null || cp -a "$src" "$dest"
}

# Many paths here are symlinks - g++/gcc/cc/c++ through /etc/alternatives/*
# to a versioned real binary (e.g. g++-13), and *every* .so found via ldd
# is potentially a `libfoo.so -> libfoo.so.1 -> libfoo.so.1.2.3`-style
# versioned symlink chain, INCLUDING the dynamic linker itself
# (/lib64/ld-linux-x86-64.so.2 -> ../lib/x86_64-linux-gnu/ld-linux-x86-64.so.2
# on this host). Staging only the final resolved target - or only the
# first hop - leaves a dangling symlink in the sandbox: the kernel then
# reports a plain, misleading "No such file or directory" execve failure
# for the *referencing* binary, not an obviously-broken-symlink error
# (confirmed via real trial and error - this broke every single
# dynamically-linked binary in the sandbox, not just the one whose
# interpreter symlink was actually dangling). Walk and stage every hop, so
# every call site below uses this instead of copy_file_only directly.
copy_symlink_chain() {
  local path="$1"
  local seen=0
  while [ -L "$path" ] && [ "$seen" -lt 10 ]; do
    copy_file_only "$path"
    local target
    target="$(readlink -- "$path")"
    case "$target" in
      /*) path="$target" ;;
      # Lexical (`realpath -s`, no symlink resolution) join+normalize -
      # NOT `readlink -f`/`realpath` (symlink-resolving), which on this
      # usrmerged host (/lib64 -> usr/lib64, /lib -> usr/lib) jumps clean
      # past intermediate hops to a DIFFERENT real path than the one this
      # specific symlink's own text implies, leaving that intermediate
      # hop's own real location unstaged (confirmed via real trial and
      # error: every dynamically-linked binary failed to exec until this
      # was single-hop, lexical-only resolution).
      *) path="$(realpath -s -- "$(dirname "$path")/$target")" ;;
    esac
    seen=$((seen + 1))
  done
  copy_file_only "$path"
}

# Recursively resolve and stage every shared library a binary needs (ldd),
# plus the binary itself and the dynamic linker.
declare -A SEEN
stage_binary_closure() {
  local bin="$1"
  [ -e "$bin" ] || { echo "warning: missing $bin" >&2; return 0; }
  copy_symlink_chain "$bin"
  local real
  real="$(readlink -f -- "$bin")"
  while read -r lib; do
    [ -z "$lib" ] && continue
    [ -n "${SEEN[$lib]:-}" ] && continue
    SEEN[$lib]=1
    copy_symlink_chain "$lib"
  done < <(ldd "$real" 2>/dev/null | grep -oP '(?<==> )/\S+|^\s*/\S+' | sed 's/^\s*//')
}

for b in "${BINARIES[@]}"; do
  stage_binary_closure "$b"
done

# The dynamic linker itself (ldd doesn't list it for the "interpreter"
# line uniformly across all binaries, so stage it explicitly).
for interp in /lib64/ld-linux-x86-64.so.2 /lib/ld-linux.so.2; do
  [ -e "$interp" ] && copy_symlink_chain "$interp"
done

# UX-925: the host gcc's internal tree, the multiarch link-time files
# (crt*.o and the unversioned dev .so linker scripts) and /usr/include
# used to be staged here, because the host compiler reached them at
# those absolute paths. The pinned closure brings its own of every one
# - start files from glibc's store path, libgcc and the C++ headers
# from gcc's, the C headers from glibc's `dev` - and
# `tools/toolchain_params.py --check` reads back that each class really
# answered from there. Staging the host's copies beside them is the
# mixture UX-925 forbids: it links and means nothing.

# UX-925: cmake's own Modules/ used to be located through `dpkg -L
# cmake-data` and staged from this host. The pin carries them inside
# its own store path, where cmake finds them relative to the binary it
# resolves - so the dpkg query, its two failed predecessors and the
# `cmake --system-information` fallback are all gone with it.

# `make`'s own recipe shell is hardcoded to /bin/sh (confirmed via a real
# "make[1]: /bin/sh: No such file or directory" failure) - this host
# aliases /bin -> usr/bin (usrmerge) but BuildStream's sandbox only stages
# exactly what's in this tree, so the alias has to be real staged content,
# not something supplied by a bwrap flag at smoke-test time.
ln -sfn usr/bin "$DEST/bin"

# UX-915: the sandbox's `make` version decides every example's jobserver
# auth style (`style_for_make_version`, UX-874), so it is pinned here
# rather than copied from whatever the staging host installed. Ubuntu
# 24.04 ships 4.3, below UX-841's 4.4 cutoff, so the `fifo` branch had
# never run in this repository's own examples and each jobserver
# element carried a `public: bga: jobserver-auth: fd` override standing
# in for that host fact. tools/nix_store_fetch.py carries the pin, its
# checksum, and why a download beats a source build here.
# UX-916 stages a 4.2 beside it, at /usr/lib/bga-make/<series>/make,
# so an element can name a version series without naming a pin hash;
# /usr/bin/make - what every element resolves by default - is the 4.4.
# UX-925: the toolchain axis, one pinned closure at its own absolute
# /nix/store prefixes. Before the make pins, because the closure
# carries the real glibc those pins' interpreter symlink stands in for
# - staged for real, it is what answers, and nix_store_fetch leaves it
# alone rather than pointing the closure's loader at this host's copy.
(cd "$HERE/.." && python3 -m tools.nix_toolchain "$DEST" >/dev/null)

# The drivers are shims rather than symlinks: neither -B nor --sysroot
# is loud when it is wrong, and the examples' own build commands invoke
# `gcc`, not a wrapper this repository controls. --shim-root defaults
# to `/`, so the flags baked in name the sandbox's paths and not this
# staging tree's (UX-930 wrote the shim; UX-925 installs it).
for driver in gcc g++ cc c++; do
  (cd "$HERE/.." && python3 -m tools.toolchain_params --shim "$driver" \
     "$DEST") > "$DEST/usr/bin/$driver"
  chmod 0755 "$DEST/usr/bin/$driver"
done

PINNED_MAKE="$(cd "$HERE/.." && python3 -m tools.nix_store_fetch "$DEST")"
MAKE_STORE_PATH="$(printf '%s\n' "$PINNED_MAKE" | awk -F'\t' '$1 == "make-4.4" {print $2}')"
PINNED_MAKE_VERSION="$(printf '%s\n' "$PINNED_MAKE" | awk -F'\t' '$1 == "make-4.4" {print $3}')"
INTERPRETER_DIR="$(cd "$HERE/.." && python3 -m tools.nix_store_fetch --interpreter-dir "$DEST")"
# Relative, not absolute: an absolute /nix/store link dangles on the
# staging host, so the verification below - and `-e` in the MISSING
# check - could not follow it. Inside the sandbox both read the same.
rm -f "$DEST/usr/bin/make"
ln -s "../..$MAKE_STORE_PATH/bin/make" "$DEST/usr/bin/make"

# The pinned binary names an absolute Nix interpreter and RUNPATH, both
# answered by nix_store_fetch's one symlink into this sysroot's own
# glibc. Run it through exactly that path rather than trusting the
# symlink's shape: a staged make that cannot exec is the failure this
# whole script's loud-verification posture exists to catch early, and
# both pins stop at GLIBC_2.38 (`objdump -T`), which is what makes the
# host's own glibc a valid answer at all.
# UX-925: and told where this tree keeps the rest of the closure. The
# pinned glibc is staged for real now, so the loader is the *pin's*,
# whose own RUNPATH is an absolute /nix/store that resolves only once
# the sandbox mounts this tree at /.
STORE_LIBS="$(cd "$HERE/.." && python3 -m tools.nix_toolchain --library-path "$DEST")"
STAGED_MAKE_VERSION="$("$DEST$INTERPRETER_DIR/ld-linux-x86-64.so.2" \
  --library-path "$STORE_LIBS" "$DEST/usr/bin/make" --version 2>&1 | head -1)"
if [ "$STAGED_MAKE_VERSION" != "$PINNED_MAKE_VERSION" ]; then
  echo "stage_cpp_toolchain.sh: the staged make reports" >&2
  echo "  $STAGED_MAKE_VERSION" >&2
  echo "but this repository pins $PINNED_MAKE_VERSION" >&2
  exit 1
fi
echo "Pinned $STAGED_MAKE_VERSION from $MAKE_STORE_PATH"
printf '%s\n' "$PINNED_MAKE" | awk -F'\t' '{print "  staged " $3 " as /usr/lib/bga-make/" substr($1, 6) "/make"}'

# Loud, early verification rather than a silent, "succeeded" staging step
# that turns out unusable three layers deep into a real build (exactly
# what happened above with cmake's Modules/ dir on a different host) -
# fail *here*, with a clear list of what's missing, not inside a cryptic
# cmake/gcc error during the real bst build this is staged for.
MISSING=()
CMAKE_MODULES="$(echo "$DEST"/nix/store/*-cmake-*/share/cmake-*/Modules/CMakeCXXInformation.cmake)"
CXX_HEADERS="$(echo "$DEST"/nix/store/*-gcc-*/include/c++)"
for f in "$DEST/usr/bin/gcc" "$DEST/usr/bin/g++" "$DEST/usr/bin/cmake" "$DEST/usr/bin/make" \
         "$DEST/usr/bin/ld" "$DEST/usr/bin/as" "$CMAKE_MODULES" \
         "$DEST$INTERPRETER_DIR/ld-linux-x86-64.so.2" \
         "$CXX_HEADERS"; do
  [ -e "$f" ] || MISSING+=("$f")
done
if [ "${#MISSING[@]}" -gt 0 ]; then
  echo "stage_cpp_toolchain.sh: staged toolchain is missing expected files:" >&2
  printf '  %s\n' "${MISSING[@]}" >&2
  exit 1
fi

# UX-925: and each driver at /usr/bin really leads to the pin. The
# version probes below ask the pin's own binary, because a shim is a
# shell script whose /nix/store paths resolve only in the sandbox - so
# a host gcc copied over a shim would answer all of them correctly.
(cd "$HERE/.." && python3 -m tools.nix_toolchain --check-shims "$DEST")

# UX-927/UX-925: every /nix/store path the staged tree names is one the
# tree carries. A reference it does not carry is one the staging host
# answered, and this reads it off the bytes rather than off a build
# that happened to succeed.
(cd "$HERE/.." && python3 -m tools.nix_closure --check "$DEST")

# UX-914: what this sysroot actually is, per package and per axis, read
# off the staged copies rather than off this host. A *pinned* row that
# disagrees exits 1 (the pin did not take, same posture as the make check
# above); a *host* row that disagrees only warns, because a different
# working host is not a broken sysroot - it is a different program under
# measurement, and the guard is what reddens for that.
(cd "$HERE/.." && python3 -m tools.sysroot_manifest --check "$DEST")

# UX-930: the versions above say what the sysroot is; this says where
# its own driver actually reaches. Every one of gcc's path parameters
# falls back to a host absolute path when the parameterized location
# is empty, and none of them says so, so each file class is asked
# rather than assumed - the reading UX-925's -B/--sysroot route needs
# before it can move the driver out of this tree.
(cd "$HERE/.." && python3 -m tools.toolchain_params --check "$DEST")

echo "Staged toolchain to $DEST ($(du -sh "$DEST" | cut -f1))"

# Every other example project that needs the identical sysroot. Hardlink
# clones (`cp -al`), not copies: BuildStream stages them as ordinary
# files, and the content is byte-identical by construction, so paying for
# a second and third ~270MB of real disk buys nothing.
for clone in \
    "$HERE/06-macro-micro-optimization/files/toolchain" \
    "$HERE/06-macro-micro-optimization/optimized/files/toolchain" \
    "$HERE/07-declared-vs-used-dependencies/files/toolchain" \
    "$HERE/08-process-storm/files/toolchain" \
    "$HERE/09-fine-grained-siblings/files/toolchain" \
    "$HERE/09-fine-grained-siblings/merged/files/toolchain" \
    "$HERE/10-jobserver/files/toolchain" \
    "$HERE/11-serial-giant/files/toolchain" \
    "$HERE/12-junctioned/sub/files/toolchain"; do
  rm -rf "$clone"
  mkdir -p "$(dirname "$clone")"
  cp -al "$DEST" "$clone"
  echo "Cloned toolchain to $clone"
done

# UX-857: examples/11-serial-giant's cmake elements reuse 10-jobserver's
# own files/gen/cmake/generate.sh (a real, committed script - not a
# generated sysroot) rather than a second copy someone has to keep in
# sync - hardlink-cloned the same way the toolchain above is, so it is
# still a real file in 11's own project directory (BuildStream's local
# source refuses a path outside it) at ~0 extra disk.
GEN_SRC="$HERE/10-jobserver/files/gen/cmake"
GEN_DEST="$HERE/11-serial-giant/files/gen/cmake"
rm -rf "$GEN_DEST"
mkdir -p "$(dirname "$GEN_DEST")"
cp -al "$GEN_SRC" "$GEN_DEST"
echo "Cloned generator to $GEN_DEST"
