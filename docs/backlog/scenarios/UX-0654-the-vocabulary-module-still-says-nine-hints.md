# UX-654: the vocabulary module still says nine hints

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** — | **Found by:** architecture review 16 | **Serves:** anyone opening `format.js` to find out what the page's vocabulary is | **Topic:** viewer

## Motivation

`bga/viewer/format.js` opens by saying what the module is:

> `app.js`'s own first seam was called `format`, and this is that
> chapter lifted out whole: **the nine `bga:` hint keys**, the readers
> that pull them off a schema node …

It is not nine, and has not been for some time:

```console
$ python3 - <<'PY'
import re, pathlib
src = pathlib.Path("bga/viewer/format.js").read_text(encoding="utf-8")
print("distinct `bga:` keys named in format.js:",
      len(set(re.findall(r"bga:[a-z_]+", src))))
body = src.split("export function hintsOf", 1)[1].split("]", 1)[0]
print("hint names hintsOf enumerates:", len(re.findall(r"\b[A-Z][A-Z_]{2,}\b", body)))
print("what the docstring says:",
      re.search(r"the (\w+) `bga:` hint keys", src).group(1))
PY
distinct `bga:` keys named in format.js: 17
hint names hintsOf enumerates: 16
what the docstring says: nine
```

`docs/design/styleguide.md` §1a says **nineteen** and carries 19 rows,
and `test_the_contract_names_its_vocabulary.py` holds that table equal
to what the schemas emit in both directions — green at this commit. The
module docstring is the
one statement of the same fact that no guard reads, so it is the one
that aged. It is the defect `UX-132` names: a figure a later round
moved and an earlier document still quotes.

The count is load-bearing in the way a reader uses it. `format.js` is
where a session goes to learn the vocabulary before adding a hint, and
"nine" tells them the set is small enough to hold in their head. It is
17 in the module and 19 in the vocabulary.

## Required Fix

The docstring stops carrying a count it cannot keep. Either it names no
number — the sentence works as *"the `bga:` hint keys"* — or the number
is derived by the guard that already reads this vocabulary, the way
`UX-632` replaced the touching figure with one `--spread --write`
derives.

Deriving is the better answer if it is cheap here:
`test_the_contract_names_its_vocabulary.py` already holds the
styleguide table against the schemas, and the third copy is one more
side of the same equality.

Whichever is chosen, the module docstring stays inside the register's
25-line bound.

## Out of Scope

- The styleguide table and its guard. Declined because both are correct
  at this commit: 19 rows, and
  `test_the_contract_names_its_vocabulary.py` green over them.
- Every other count in a viewer module docstring. This row is the one
  the review measured; a sweep is a different row, and would want the
  population derived rather than grepped.

## Acceptance Test

`format.js`'s opening paragraph carries no figure the tree can move
past, or carries one a guard reddens on. Mutation: adding an
eighteenth `bga:` key to the module reddens the guard, or — for the
no-number fix — `grep -c "nine .bga:. hint keys" bga/viewer/format.js`
returns 0.
