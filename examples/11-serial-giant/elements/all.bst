# Real build target - three leaves, each pulling giant.bst in as a
# build dependency, plus UX-916's two version-switch arms, which wait
# on nothing but the toolchain.
kind: stack
depends:
- leaf-a.bst
- leaf-b.bst
- leaf-c.bst
- switch-4-4.bst
- switch-4-2.bst
