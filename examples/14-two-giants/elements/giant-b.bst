# UX-1132: the second giant, identical to giant-a.bst but for its
# name. Parallel on purpose: `notparallel: True` here is the Acceptance
# Test's mutation, and the two-giants width check fails on it.
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
  - sh generate.sh giant_b 256 %{giant_lines}
  - |
    %{cmake}
