# The single highest-blast-radius element (5 downstream: lib-a..d +
# app) - still deliberately the slowest single step, but cut from
# `sleep 4` to `sleep 2` per docs/optimization-walkthrough.md's
# opportunity #2.
kind: manual
depends:
- filename: base.bst
  type: build
- filename: runtime.bst
  type: build
config:
  install-commands:
  - "sleep 2"
