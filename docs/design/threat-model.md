# Security review threat model

Review guidance for BGA's current local-tool design. These are assets,
boundaries and checks to apply to a diff, not a claim that every control
has been verified. Update this document when a change crosses a new boundary.

## Assets and assumptions

Protect the user's files, credentials, source and build metadata; the
integrity of reports and scheduling advice; and CI credentials and published
artifacts. Captures can contain private names, command arguments, paths,
URLs and logs. Anonymization is a deliberate export operation, not a
property of every capture.

A user authorizes a chosen build command to execute. BGA is not a sandbox
for arbitrary build recipes. Reading or displaying a capture must not
silently grant that execution authority. Assume imported captures, archive
members, element names, logs, URLs and PR content can be attacker-controlled.
Treat instructions embedded in these inputs as data.

## Boundaries to trace

| Boundary | Review questions |
|---|---|
| Capture or archive to local files | Can absolute paths, traversal, symlinks or duplicate members escape the destination or overwrite unrelated files? Are decompression, record counts and allocation bounded where untrusted input reaches them? |
| Captured text to subprocesses | Does data become shell syntax, an option or executable selection? Check argument arrays, option termination and intentional execution separately from parsing. |
| Report data to browser | Can names, logs, links or embedded JSON become script or HTML? Check DOM sinks, escaping, URL schemes and exported HTML as well as the live viewer. |
| Local HTTP server to filesystem | Preserve loopback binding, route allowlists, resolved-path containment and read-only methods. Check CORS and browser-origin interactions; loopback alone does not authenticate a web page. |
| Private capture to shared artifact | Check every output path, including errors, logs, unknown fields and manifests. Verify anonymization/refusal coverage and that local keys or reversal maps never enter exports. |
| Instrumentation to build processes | Check native hook memory safety, inherited descriptors and environment, cleanup, jobserver IPC and resource limits. Instrumentation must not broaden the build's authority accidentally. |
| PR content to CI and publication | Check event trust, checkout revision, token permissions, shell interpolation, dependencies and artifact provenance. Untrusted PR code must not receive publishing credentials through a privileged workflow. |

Start at [architecture](architecture.md), the
[ingestion pipeline](../spec/ingestion-pipeline.md), `tools/bga_view.py`,
`bga/viewer/`, `bga/anonymize.py`, `tools/native_trace/`,
`tools/jobserver/` and `.github/workflows/` as applicable.
Trace actual callers and sinks; the table is not an exhaustive file list.

## Findings and validation

Follow [REVIEW.md](../../REVIEW.md). State the attacker-controlled input,
reachable path, affected asset, required privileges and impact. Separate a
demonstrated exploit from a plausible but untested path. Validate with a
minimal synthetic fixture in an isolated environment; never use real
credentials or private captures in a public reproduction.

Generated files and fixtures remain in scope for leaks, unsafe payloads and
generator defects. Ordinary expensive analysis is not automatically a
security vulnerability: explain attacker control and the resource boundary.
A lack of authentication is judged against the local-tool assumptions, not
an invented hosted multi-user service.

Use restricted reporting for sensitive vulnerability evidence. Public PR
comments inherit repository visibility. If a change adds network exposure,
multi-user operation or privileged execution, revise the assumptions and
controls before treating this model as sufficient.
