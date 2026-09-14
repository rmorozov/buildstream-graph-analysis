# Real build target - three leaves, each pulling giant.bst in as a
# build dependency.
kind: stack
depends:
- leaf-a.bst
- leaf-b.bst
- leaf-c.bst
