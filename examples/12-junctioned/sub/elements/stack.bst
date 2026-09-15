# Groups the one cmake element - the top project depends on
# `junction.bst:stack.bst`, not on `junction.bst:core.bst` directly, so
# the subproject owns its own build target the way a real junctioned
# project does.
kind: stack
depends:
- core.bst
