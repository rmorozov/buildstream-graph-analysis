# Post the verdict where the reviewer will read it

`bga` can already decide. `bga compare --fail-on-inefficient-additions`
exits 5 when a change serialized the work it added, and
`--fail-on-regression` exits 4 when the build got slower than its band.
What a CI owner got back was an exit code and, if they asked, a JSON
blob.

That gap is not cosmetic. **A gate that fails with a wall of JSON gets
its threshold loosened; a gate that fails by naming the element gets the
element fixed.** `bga compare --format ci-comment` renders the verdict
the gate already reached as markdown a reviewer reads in the pull
request.

It computes nothing. Every number in it is a field of the comparison
`--format json` already publishes, and every gate verdict comes from the
same predicate the exit code is derived from — so the comment and the
pipeline's decision cannot disagree.

## What it looks like

Rendered from two real builds of
`examples/06-macro-micro-optimization/optimized`, the second with two
libraries added serialized behind the existing fan-out:

```markdown
<!-- bga-ci-comment -->

### Build efficiency

**REGRESSED** — wall-clock 17.5s → 20.4s (+2.9s, +16.7%)

judged against the fixed 1% rule (no baseline set supplied)

| Gate | Result | Why |
| --- | --- | --- |
| Marginal efficiency | FAIL | 6.0s of the 6.0s this change added landed on the critical path (stretch 1.00 > 0.50) |
| Whole-build efficiency | pass | occupancy 65% (-0.8pp) |
| Wall-clock regression | FAIL | +2.9s (+16.7%) — outside the fixed 1% rule |

**Elements this change added or moved**

| Element | Duration | Critical path | Declared, never read |
| --- | ---: | --- | --- |
| `lib-g.bst` | 4.0s | yes — new on the path | `core.bst`, `lib-f.bst` |
| `lib-h.bst` | 2.0s | yes — new on the path | `core.bst`, `lib-g.bst` |
| `lib-f.bst` | 6.0s | yes — moved onto the path | `codegen.bst`, `core.bst` |

**Cache** — churn not measured: the candidate is a caches-off run, so every element rebuilt by instruction - an unchanged cache key there is the intended behaviour, not waste.

<sub>baseline 2026-08-19 12:58:14 UTC · candidate 2026-08-19 12:58:52 UTC</sub>
```

The last column is the one that turns a verdict into a fix:
`lib-h.bst` declares a build dependency on `lib-g.bst`, and Plane 2
observed nothing in its sandbox opening a file `lib-g.bst` staged. The
edge that cost 2.0s of critical path is not carrying anything.

## Reading it

- **The headline** is the band verdict. With `--baseline-run` supplied
  three or more times (or via `bga baseline`) the second line names the
  measured noise band instead of the fixed 1% rule.
- **Every gate appears, every time.** A gate the invocation did not ask
  for reads `not requested`; a gate that could not run — no
  `occupancy_ratio` in a run, or a change that added no measured work —
  reads `not applied`, with the reason. Neither is a pass. A comment
  that showed only the gates which fired would read as a clean bill of
  health from a pipeline that checked nothing.
- **The element table** lists what the change added and what it pushed
  onto the critical path, capped at eight rows with the rest collapsed.
- **The `Declared, never read` column only exists with Plane 2 data.**
  Without `--native-report` it is absent and the comment says so —
  "nothing was staged and never read" and "nobody looked" are different
  claims, and an empty column would assert the first.
- **The trailing line is the run instance** (`UX-95`), not the run
  identity. Two pushes of the same tree produce identical identity
  hashes; only the instant tells the two comments apart.

## Wiring it into GitHub Actions

The comment carries a marker, `<!-- bga-ci-comment -->`, as its first
line. Find the existing comment by that marker and edit it, rather than
posting a new one on every push — otherwise a branch with ten pushes
carries ten comments and the reviewer reads the stale one.

```yaml
- name: Capture the candidate build
  run: |
    bga wrap "$PROJ" candidate-build.log -- bst build "$TARGET"
    bga extract "$PROJ" candidate-build.log runs/candidate

- name: Compare against the published baseline set
  id: compare
  run: |
    # The gate's exit code is captured, not acted on yet: the reviewer is
    # told why before the check goes red.
    SHORT_COMMIT="$(echo "${{ github.sha }}" | cut -c1-8)"
    set +e
    bga baseline \
      --glob "captures/$PROJ/$SHORT_COMMIT-incremental-b4j4-*" -n 3 \
      --candidate runs/candidate \
      -- --format ci-comment --fail-on-inefficient-additions > compare-output.txt
    rc=$?
    set -e
    cat compare-output.txt
    sed -n '/<!-- bga-ci-comment -->/,$p' compare-output.txt > comment.md
    echo "rc=$rc" >> "$GITHUB_OUTPUT"

- name: Post or update the comment
  uses: actions/github-script@v7
  with:
    script: |
      const fs = require('fs');
      const body = fs.readFileSync('comment.md', 'utf8');
      const marker = '<!-- bga-ci-comment -->';
      const { owner, repo } = context.repo;
      const issue_number = context.issue.number;
      const existing = (await github.rest.issues.listComments({
        owner, repo, issue_number,
      })).data.find(c => c.body.startsWith(marker));
      if (existing) {
        await github.rest.issues.updateComment({
          owner, repo, comment_id: existing.id, body });
      } else {
        await github.rest.issues.createComment({
          owner, repo, issue_number, body });
      }

- name: Re-apply the gate's verdict
  run: exit ${{ steps.compare.outputs.rc }}
```

Two details that are load-bearing:

- **`rc=$?` reads `bga`, not `sed`.** The gate's status is captured
  from the command itself and the extraction happens afterwards against
  a file. Piping `bga` into `sed` and reading `$?` would report *`sed`'s*
  exit code, which is 0 whatever the gate decided — the same
  `tee`-swallows-the-status trap `UX-97` recorded in this repo's own CI.
- **`sed -n '/<!-- bga-ci-comment -->/,$p'`** — `bga baseline` prints
  its own set listing (which refs it fetched, which fields it had to
  assume, whether the capture tooling drifted) before handing off to
  `bga compare`. That belongs in the job log, not in the comment.
- **The exit code is re-applied last.** Posting the comment and then
  failing gives the reviewer the explanation *and* the red check. A job
  that fails before commenting gives them only the red check, which is
  the situation this whole feature exists to end.

With Plane 2 in the pipeline, add `--native-report` to the `bga compare`
arguments to get the never-read column. Capture both planes from **one**
build — `--run-dir` (`UX-126`) writes the run directory from the same
`bst` invocation, replacing the `wrap` + `extract` pair above rather
than adding a second build to it:

```bash
bga capture run --trace-opens --run-dir runs/candidate \
  "$PROJ" native.json -- bst build "$TARGET"
bga compare runs/baseline runs/candidate \
  --format ci-comment --native-report native.json
```

Two builds would put the never-read column on a different build from the
one the verdict describes, and the join would correlate one build's
sandboxes against the other's timeline.

## What it deliberately does not do

- **No new metrics and no new thresholds.** If a number is not already
  in `bga compare --format json`, it is not in the comment.
- **No forge beyond the example.** The markdown is the product; the
  `actions/github-script` step above is one way to deliver it.
- **No summary of the whole repository.** The comment judges the change.
  `bga analyze` is where the repository's own shape is reported.

## See also

- [`cli.md`](cli.md) — every flag and exit code, including the gates
  this renders.
- [`real-project.md`](real-project.md) — capture, read, fix, prove, gate,
  end to end.
