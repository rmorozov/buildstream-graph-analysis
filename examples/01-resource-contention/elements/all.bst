# Real build target - forces all eight independent work-*.bst elements
# into one session so BuildStream's scheduler actually has to contend for
# a constrained builder count (see examples/README.md for the exact
# invocation this project is built with).
kind: stack
depends:
- work-a.bst
- work-b.bst
- work-c.bst
- work-d.bst
- work-e.bst
- work-f.bst
- work-g.bst
- work-h.bst
