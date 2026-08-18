# UX-84: the fixture's real, BuildStream-honoured per-element
# parallelism control. `variables: notparallel: True` is the only one
# BuildStream 2.7 actually reads (UX-31); it resolves `%{max-jobs}` to 1
# for this element while every sibling keeps the project default. That
# difference is what tools/bst_show_to_graph.py's UX-31 capture exists
# to see, and what `manual.bst`'s ignored `public: bst: max-jobs: 16`
# cannot demonstrate.
#
# Not a dependency of app.bst, so it does not affect the other tests
# against this fixture.
kind: manual
depends:
- filename: base.bst
  type: build
variables:
  notparallel: True
config:
  install-commands:
  - "true"
