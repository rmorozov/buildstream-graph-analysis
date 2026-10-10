# Audits

What was found, and when. Append-only by nature: each round is a
timestamped record, not a statement of current state.
[`round-register.md`](round-register.md) derives which rounds happened
and when; this page links each one.

These are not rounds. They stand outside the sequence and are appended
to instead of superseded:

| document | what it records |
|---|---|
| [`architecture-review.md`](architecture-review.md) | every architecture and documentation review the `UX-241` cadence has called; its log table runs newest last, its sections do not (reviews 1-20 roughly in order, then 36 down to 21) — **append-only**, so a superseded finding stays where it was written and the review after it says so |
| [`spec-compliance-review.md`](spec-compliance-review.md) | the original review of the tool against its specification, before the round sequence began |
| [`walk-seed-1.md`](walk-seed-1.md) | `UX-685`'s first seeded walk — 1 element, Plane 2 absent, real Chrome; the seed names it and reruns it |
| [`walk-seed-2.md`](walk-seed-2.md) | `UX-685`'s second seeded walk — the empty-population class, hook-only Plane 2, the static export |
| [`walk-seed-3.md`](walk-seed-3.md) | `UX-685`'s third seeded walk — the process storm, spine on, cold then incremental, real Chrome |
| [`walk-seed-4.md`](walk-seed-4.md) | the 0.5.0 release walk at `74aa14f2` — `macro_micro` standing in for a capture, real Chrome; `UX-1135` filed from it |
| [`walk-seed-5.md`](walk-seed-5.md) | the 0.6.0 release walk at `3e3657a7` — `macro_micro` standing in for a capture, real Chrome; `UX-1341`, `UX-1342` filed from it |
| [`agent-runs.md`](agent-runs.md) | what each subagent run cost — tokens, tool calls, wall clock — and its own friction line, one row per run, so a model and a report shape are chosen from numbers (`UX-666`) |
| [mutation.md](https://github.com/rmorozov/buildstream-graph-analysis/blob/records/docs/audits/mutation.md) | the weekly mutation run's survivors — a mutant the touched modules' own guards did not kill, one dated section per run. A survivor is a filing, not a failure (`UX-703`); gitignored since `UX-997` T2 — `tools/dev_records.py fetch` writes it locally, `refs/heads/records` carries it |
| [`round-register.md`](round-register.md) | which rounds happened and when, derived from the committed union — every round document, the ledger's round column and every round a task file names, never `git log` — dated by the document's own dateline; only the one next round, still without its document, is held out of it (`UX-744`, `UX-782`, `UX-926`) |
| [`directions-history.md`](directions-history.md) | the round, status and verification chapters `design/directions.md` carried between its Directions, and the round-history table every round adds a row to (`UX-1293`) |
| [`retro-2026-09-28.md`](retro-2026-09-28.md) | the first weekly retro (`UX-999`) — the week's findings by class, main's CI history, three `optimization` proposals |
| [`retro-2026-10-05.md`](retro-2026-10-05.md) | the second weekly retro — the ledger by class, main's 3.9 cell red since 2026-09-29 on a dev pin above the floor, three `optimization` proposals |

The rounds themselves:

[`round-2.md`](round-2.md) ·
[3](round-3.md) ·
[4](round-4.md) ·
[5](round-5.md) ·
[6](round-6.md) ·
[7](round-7.md) ·
[8](round-8.md) ·
[9](round-9.md) ·
[10](round-10.md) ·
[11](round-11.md) ·
[12](round-12.md) ·
[13](round-13.md) ·
[14](round-14.md) ·
[15](round-15.md) ·
[16](round-16.md) ·
[17](round-17.md) ·
[18](round-18.md) ·
[19](round-19.md) ·
[20](round-20.md) ·
[21](round-21.md) ·
[22](round-22.md) ·
[23](round-23.md) ·
[24](round-24.md) ·
[27](round-27.md) ·
[40](round-40.md) ·
[41](round-41.md) ·
[43](round-43.md) ·
[44](round-44.md) ·
[45](round-45.md) ·
[46](round-46.md) ·
[63](round-63.md) ·
[64](round-64.md) ·
[74](round-74.md) ·
[75](round-75.md) ·
[76](round-76.md) ·
[77](round-77.md) ·
[78](round-78.md) ·
[79](round-79.md) ·
[80](round-80.md) ·
[81](round-81.md) ·
[82](round-82.md) ·
[83](round-83.md) ·
[84](round-84.md) ·
[85](round-85.md) ·
[86](round-86.md) ·
[87](round-87.md) ·
[88](round-88.md) ·
[89](round-89.md) ·
[90](round-90.md) ·
[91](round-91.md) ·
[92](round-92.md) ·
[93](round-93.md) ·
[94](round-94.md) ·
[95](round-95.md) ·
[99](round-99.md) ·
[100](round-100.md) ·
[101](round-101.md) ·
[102](round-102.md) ·
[103](round-103.md) ·
[104](round-104.md) ·
[105](round-105.md) ·
[106](round-106.md) ·
[107](round-107.md) ·
[108](round-108.md) ·
[109](round-109.md) ·
[110](round-110.md) ·
[111](round-111.md) ·
[112](round-112.md) ·
[113](round-113.md) ·
[114](round-114.md) ·
[115](round-115.md) ·
[116](round-116.md) ·
[117](round-117.md) ·
[118](round-118.md) ·
[119](round-119.md) ·
[120](round-120.md) ·
[121](round-121.md) ·
[122](round-122.md) ·
[123](round-123.md) ·
[124](round-124.md) ·
[125](round-125.md) ·
[126](round-126.md) ·
[127](round-127.md) ·
[128](round-128.md) ·
[129](round-129.md) ·
[130](round-130.md) ·
[131](round-131.md) ·
[134](round-134.md) ·
[135](round-135.md) ·
[136](round-136.md) ·
[137](round-137.md) ·
[138](round-138.md) ·
[139](round-139.md) ·
[140](round-140.md) ·
[141](round-141.md) ·
[142](round-142.md) ·
[143](round-143.md) ·
[144](round-144.md) ·
[145](round-145.md) ·
[146](round-146.md) ·
[147](round-147.md) ·
[148](round-148.md) ·
[149](round-149.md) ·
[150](round-150.md) ·
[151](round-151.md) ·
[152](round-152.md) ·
[153](round-153.md) ·
[154](round-154.md) ·
[155](round-155.md) ·
[156](round-156.md) ·
[157](round-157.md) ·
[158](round-158.md) ·
[159](round-159.md) ·
[160](round-160.md) ·
[161](round-161.md) ·
[163](round-163.md) ·
[165](round-165.md) ·
[166](round-166.md) ·
[168](round-168.md) ·
[169](round-169.md) ·
[170](round-170.md) ·
[171](round-171.md) ·
[the guard census of round 64](guard-census-round-64.md)

## Case studies

Records of real sessions, kept verbatim. They are evidence, not
instructions — their commands are the ones those rounds ran, not the
ones to run today (`UX-139`).

| document | what it records |
|---|---|
| [`case-study-06-macro-micro.md`](case-study-06-macro-micro.md) | the macro-then-micro cycle, **including where the tool did not guide the user** |
| [`optimization-walkthrough-04.md`](optimization-walkthrough-04.md) | the retired `sleep N` proxy walkthrough, kept for provenance |
| [`planted-defect-walk-round-72.md`](planted-defect-walk-round-72.md) | three defects **chosen first**, generated into real projects, and how far the front door gets each reader towards the planted answer (`UX-468`) |
| [`perf-snapshot-view-2026-09-28.md`](perf-snapshot-view-2026-09-28.md) | bga's **own** cost after the build and before the page: the tail's four analyzer runs, a quadratic closure, silent phases, measured at 74, 1,202 and 5,002 elements (`UX-1072`..`UX-1081`) |
| [`quality-gates-2026-09-29.md`](quality-gates-2026-09-29.md) | the gates themselves: CI's 56-minute PR path and where it goes, the push gate's markdown scan, what the suite guards and what no check covers (`UX-1108`..`UX-1122`) |
| [`perf-analyze-profile-2026-09-28.md`](perf-analyze-profile-2026-09-28.md) | `bga analyze` after round 150, per stage: graph-only 4.00 s against Plane 1 7.06 s at 5,002 elements; the blast radius decode is 332 of 469 MB (`UX-1106`) |
