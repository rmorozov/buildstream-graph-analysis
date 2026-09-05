# UX-654: the vocabulary module still says nine hints

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** architecture review 16 | **Serves:** anyone opening `format.js` to find out what the page's vocabulary is | **Topic:** viewer

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

## Outcome (round 89, 2026-09-04) — 🟢 Done

**Derived, and each figure names its population.** The sentence keeps
numbers; both are recomputed by
`test_the_contract_names_its_vocabulary.py`, the guard that already
holds the schemas against §1a:

```console
$ sed -n 4,9p bga/viewer/format.js
 * `app.js`'s own first seam was called `format`, and this is that
 * chapter lifted out whole: the 17 `bga:` hint keys this module
 * declares (of the 19 `bga/schemas.py` emits), the readers that pull
 * them off a schema node (`hintsOf`, `childNode`, `quantityFor`), the
 * formatters that turn a number into a printed value under them, and
 * `el` - the one node constructor everything above builds with.
```

**Why deriving and not dropping the number.** Three populations are
live and no two are equal, so "the `bga:` hint keys" with no figure
would leave the reader who came here to add a hint with no size for
the set, and nothing would redden when a later round wrote a count
back in:

```console
$ python3 - <<'EOF'   # declared | emitted | hintsOf | emitted-not-declared
import re, pathlib
f = pathlib.Path("bga/viewer/format.js").read_text()
s = pathlib.Path("bga/schemas.py").read_text()
d = set(re.findall(r'^(?:export )?const \w+ = "(bga:[\w-]+)";', f, re.M))
e = set(re.findall(r'"(bga:[\w-]+)"', s))
h = f.split("export function hintsOf", 1)[1].split("]", 1)[0]
print(len(d), len(e), len(re.findall(r"\b[A-Z][A-Z_]{2,}\b", h)),
      sorted(e - d), sorted(d - e))
EOF
17 19 16 ['bga:always_written', 'bga:markers'] []
```

**Where this task file was wrong.** It offers deriving as "one more
side of the same equality". It is not an equality: `format.js`
declares a strict **subset**, 17 of 19, missing `bga:always_written`
and `bga:markers`. So the third side is two counts and a subset
claim — three assertions, not one line. Cheap, but a different shape
from the equality already there.

**The close.**

```console
$ python3 -m pytest tests/unit/test_the_contract_names_its_vocabulary.py -q
10 passed in 0.08s
$ make test-touching
23 file(s) selected (11 census + 12 naming the change) · 638 passed, 10 skipped in 20.17s
$ grep -c "nine .bga:. hint keys" bga/viewer/format.js
0
```

**Mutations**, each reverted from a copy taken before the first.

| mutation | expected | got |
|---|---|---|
| `const MARKERS = "bga:markers";` appended — an eighteenth key, emitted, so the subset still holds | only the declared count reddens | `test_the_count_of_keys_the_module_declares`: `says it declares 17 … and declares 18`. 1 failed, 9 passed |
| the sentence's `of the 19` → `of the 18` | only the emitted count reddens | `test_the_size_of_the_vocabulary_it_is_part_of`: `assert 18 == 19`. 1 failed, 9 passed |
| `const ROLE = "bga:role"` → `"bga:roles"`, set size unchanged | only the subset claim reddens | `test_the_keys_it_declares_are_drawn_from_that_vocabulary`: `emitted by nothing: ['bga:roles']`. 1 failed, 9 passed |
| both figures cut back out of the sentence | both count guards redden on the missing statement | 2 failed, 8 passed |

The third separates them: it moves a member without moving the count,
so the count test stays green and only the subset test falls.

**Deviation.** The comment block grew one line, 21 to 22, against the
register's 25 — the population had to be named for the number to mean
anything (`awk 'NR==1,/\*\//{n++}'`, before and after).
