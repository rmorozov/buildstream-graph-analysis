# One of three small leaves (see leaf-a.bst, leaf-b.bst) that wait on
# giant.bst - the shape UX-857 exists to show: nothing else can start
# until the one long element finishes, so its own cap is the whole
# critical path's cap. 8 generated C files, same generator as
# giant.bst, a tenth its size.
kind: cmake
depends:
- filename: toolchain.bst
  type: build
- filename: giant.bst
  type: build
sources:
- kind: local
  path: files/gen/cmake
variables:
  generator: Unix Makefiles
config:
  configure-commands:
  - sh generate.sh leaf_c 8 1800
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
