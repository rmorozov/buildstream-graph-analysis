# Added for tools/bst_checkout_cost.py's real end-to-end test
# (tests/unit/test_bst_checkout_cost.py) - a `kind: stack` element
# grouping base.bst/base2.bst for a real "individual checkouts vs. one
# stack checkout" comparison. Not a dependency of app.bst (the target
# other tests against this fixture use), so it doesn't affect them.
kind: stack
depends:
- base.bst
- base2.bst
