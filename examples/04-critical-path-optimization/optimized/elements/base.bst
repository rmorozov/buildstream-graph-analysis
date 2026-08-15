# The structural fix: base-config.bst + base-generate.bst merged into
# one step. Both were `manual` elements with no real dependency on each
# other's *output* (base-generate.bst only depended on base-config.bst
# because of an unnecessary serial split) - one `sleep 1` replaces two,
# removing 1s from the critical path with no loss of real work.
kind: manual
depends:
- filename: runtime.bst
  type: build
config:
  install-commands:
  - "sleep 1"
