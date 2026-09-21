# UX-857: the long element. `files/gen/cmake/generate.sh` (example 10's
# own script, hardlink-cloned in, not copied) writes 256 generated C
# files, a header, a main(), and a CMakeLists.txt inside the sandbox -
# four times 10's per-element 64. `9800` lines/file (10's own 1800
# compiled in ~0.13s here - `cc1` CPU was under half the element's own
# measured CPU): standalone on this host, `gcc -c` on one such file is
# ~0.47-0.55s, and `cc1` alone is 87-90% of the element's own measured
# CPU (UX-857's Outcome has the full split, including what does not
# shrink as a share just because compile CPU grows). Alone on the
# critical path (leaf-a/b/c all depend on it, below) with `max-jobs: 2`
# (xdg_config_home/), so `off` caps it at -j2 while three of this box's
# four cores sit idle.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
sources:
- kind: local
  path: files/gen/cmake
variables:
  generator: Unix Makefiles
config:
  configure-commands:
  - sh generate.sh giant 256 9800
  - |
    %{cmake}

# UX-913: force the fd auth style. The sandbox's make is the host's
# (GNU Make 4.3), which rejects a `fifo:` auth, so UX-874 downgrades to
# `fd` and UX-878's compiler-safety guard then scrubs it outright - the
# capture warns `scrubbed to recipe -jN` and the element runs at its own
# `-j2` under `auto` as much as under `off`. UX-878 guards an unwrapped
# grandchild (gcc's lto-wrapper); here the consumer is `make`, a direct
# child, and this element requests no LTO.
public:
  bga:
    jobserver-auth: fd
