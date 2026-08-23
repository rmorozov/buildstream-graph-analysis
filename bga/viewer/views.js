// UX-196: three views where a drawing says what sentences strain to.
//
// The discipline from UX-193 still holds: these render *published*
// payloads, and they draw only where the generic table genuinely cannot
// say it. That is exactly two SVGs - the band strip and the store trend
// - and no library behind either. Everything else here is layout.
//
// Nothing below recomputes anything. `compare/v1` already carries the
// band edges, the observed extent and the verdict; `store/v1` already
// carries the sizes and the incomplete reasons. A viewer that did its
// own arithmetic would be a second implementation of the analysis, and
// the first thing it would do is disagree with the first one.

const SVG = "http://www.w3.org/2000/svg";

function svg(tag, attrs = {}) {
  const node = document.createElementNS(SVG, tag);
  for (const [name, value] of Object.entries(attrs)) {
    if (value !== null && value !== undefined) node.setAttribute(name, String(value));
  }
  return node;
}


// Small local formatters rather than importing app.js's: app.js already
// imports *this* module, and a cycle between the two would work today
// (both export hoisted declarations) and break the first time either
// grows a top-level side effect. `UX-201` folds formatting into one
// schema-driven place, which is where this duplication goes to die.
function seconds(microseconds) {
  const s = microseconds / 1e6;
  return s < 90 ? `${s.toFixed(1)} s` : `${(s / 60).toFixed(1)} min`;
}

function mib(value) {
  const units = ["B", "KiB", "MiB", "GiB"];
  let n = value, i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i += 1; }
  return `${i === 0 ? n : n.toFixed(1)} ${units[i]}`;
}

// --------------------------------------------------------------- band
//
// `UX-170`'s disputed region is the case this drawing exists for: a
// candidate outside the noise band but inside the range the baseline
// runs actually spanned. In prose that took a paragraph and still read
// like a paradox. Drawn, the marker simply lands between the strip's
// edge and the dots' extent, and the question answers itself.

export function bandGeometry(compare) {
  const band = compare.baseline_band;
  if (!band) return null;

  const low = band.band_low_us ?? band.low_us ?? band.low;
  const high = band.band_high_us ?? band.high_us ?? band.high;
  const observedLow = band.observed_low_us ?? band.min_us ?? low;
  const observedHigh = band.observed_high_us ?? band.max_us ?? high;
  const candidate = compare.candidate?.total_duration_us;
  if ([low, high, candidate].some((v) => typeof v !== "number")) return null;

  // The axis spans whichever is wider - the band or what was observed -
  // with a margin so a candidate just outside is still on the canvas.
  const lo = Math.min(low, observedLow, candidate);
  const hi = Math.max(high, observedHigh, candidate);
  const pad = (hi - lo) * 0.1 || 1;
  const min = lo - pad, max = hi + pad;
  const at = (value) => ((value - min) / (max - min)) * 100;

  const inBand = candidate >= low && candidate <= high;
  const inObserved = candidate >= observedLow && candidate <= observedHigh;
  return {
    min, max, at,
    band: { low, high, x: at(low), width: at(high) - at(low) },
    observed: { low: observedLow, high: observedHigh,
                x: at(observedLow), width: at(observedHigh) - at(observedLow) },
    candidate: { value: candidate, x: at(candidate) },
    runs: (band.runs ?? band.baseline_runs ?? [])
      .map((r) => (typeof r === "number" ? r : r.total_duration_us))
      .filter((v) => typeof v === "number")
      .map((value) => ({ value, x: at(value) })),
    // The three-way answer, taken from the payload's own verdict where
    // it has one rather than re-derived from the numbers.
    where: inBand ? "inside the band"
      : inObserved ? "outside the band, inside the observed range"
      : "outside both",
    disputed: !inBand && inObserved,
  };
}

export function renderBand(compare) {
  const geometry = bandGeometry(compare);
  if (!geometry) return null;

  const H = 74;
  const figure = svg("svg", {
    viewBox: `0 0 100 ${H}`, class: "band", preserveAspectRatio: "none",
    role: "img", "data-where": geometry.where,
    "data-disputed": String(geometry.disputed),
    "data-candidate-x": geometry.candidate.x.toFixed(3),
    "data-band-x": geometry.band.x.toFixed(3),
    "data-band-width": geometry.band.width.toFixed(3),
    "data-observed-x": geometry.observed.x.toFixed(3),
    "data-observed-width": geometry.observed.width.toFixed(3),
  });
  // UX-212: the two rectangles differed by fill alone, and the caption
  // was doing the work the drawing should. The extent is drawn open -
  // a dashed outline around what the baselines *reached* - and the
  // band solid, because the band is the claim and the extent is its
  // context. Presentation attributes, so `filter: grayscale` cannot
  // take them away.
  figure.append(svg("rect", {
    x: geometry.observed.x, width: geometry.observed.width,
    y: 18, height: 26, class: "observed", "data-role": "observed",
    "data-outline": "dashed", "stroke-dasharray": "2 1.5",
    "stroke-width": 0.6, "fill-opacity": 0.35,
  }));
  figure.append(svg("rect", {
    x: geometry.band.x, width: geometry.band.width,
    y: 24, height: 14, class: "band-strip", "data-role": "band",
    "data-outline": "solid", "stroke-width": 0.6,
  }));
  for (const run of geometry.runs) {
    figure.append(svg("circle", {
      cx: run.x, cy: 31, r: 1.4, class: "baseline-dot", "data-role": "run",
      "data-value": run.value,
    }));
  }
  figure.append(svg("line", {
    x1: geometry.candidate.x, x2: geometry.candidate.x, y1: 8, y2: 54,
    class: "candidate", "data-role": "candidate",
    "data-value": geometry.candidate.value,
  }));

  const wrapper = document.createElement("section");
  wrapper.setAttribute("data-section", "band");
  const heading = document.createElement("h2");
  heading.textContent = "The band";
  // UX-209: the answer in one sentence. The long explanation is kept -
  // nothing is removed from the page or the export - but it stops
  // re-teaching `UX-170` at paragraph length on every render, to
  // readers whose comparison is not even disputed.
  const caption = document.createElement("p");
  caption.className = "muted";
  caption.textContent = geometry.disputed
    ? "The candidate is outside the noise band but inside the range the "
      + "baselines themselves spanned, so compare declines to call it."
    : `The candidate is ${geometry.where}.`;
  wrapper.append(heading, figure, caption);
  if (geometry.disputed) {
    const why = document.createElement("details");
    why.className = "muted";
    why.setAttribute("data-fold", "band-why");
    const summary = document.createElement("summary");
    summary.textContent = "Why this is not a regression";
    const body = document.createElement("p");
    body.textContent =
      "The marker sits between the strip and the dots' extent: the "
      + "baseline set is too scattered for its own band to contain it. "
      + "UX-170 calls this the disputed region - a set that cannot "
      + "support the claim, rather than a run that got worse.";
    why.append(summary, body);
    wrapper.append(why);
  }
  return wrapper;
}

// UX-212: a second channel for the verdict.
//
// The trend encoded `verdict_kind` as fill colour alone, so the one
// chart that answers "is this project drifting" said nothing about
// which way under `filter: grayscale`, a monochrome print, or the
// muted palettes some themes produce. The precedent was already in
// this function: an incomplete snapshot is a *square*, because that
// difference survives anything.
//
// Shape, not colour, and named in a `data-marker` attribute so the
// encoding is something a reader (and a guard) can read off the
// element rather than infer from a stylesheet.
//
// *Which* shape is the schema's answer, not this file's: a map from
// verdict kind to shape lives on `store/v1`'s `verdict_kind` node,
// where it is validated to cover the vocabulary and to give no two
// kinds the same shape. `UX-214` is the reason - a second list of
// verdict kinds in JavaScript is a vocabulary waiting to diverge - and
// it is why nothing here names a verdict.
export function verdictMarkers(schema) {
  return schema?.properties?.snapshots?.items
    ?.properties?.verdict_kind?.["bga:markers"] ?? {};
}

export function verdictMarker(kind, markers = {}) {
  return markers[kind] ?? "circle";
}

/** One trend point, drawn as its verdict's shape. */
function markerPoint(marker, cx, cy, r, attrs) {
  // `data-cy` on every marker, whatever its shape: the y position is
  // the answer the chart gives, and a guard reading it should not have
  // to know whether this verdict happened to draw a circle.
  const shaped = { ...attrs, "data-marker": marker, "data-cy": cy };
  if (marker === "circle" || marker === "circle-open") {
    return svg("circle", {
      cx, cy, r,
      ...(marker === "circle-open"
        ? { "stroke-dasharray": `${(r * 0.9).toFixed(2)} ${(r * 0.6).toFixed(2)}`,
            "stroke-width": 0.7, "fill-opacity": 0.25 }
        : {}),
      ...shaped,
    });
  }
  const points = marker === "triangle-up"
    ? [[cx, cy - r * 1.25], [cx + r * 1.2, cy + r], [cx - r * 1.2, cy + r]]
    : marker === "triangle-down"
      ? [[cx, cy + r * 1.25], [cx + r * 1.2, cy - r], [cx - r * 1.2, cy - r]]
      : [[cx, cy - r * 1.4], [cx + r * 1.4, cy], [cx, cy + r * 1.4],
         [cx - r * 1.4, cy]];
  return svg("polygon", {
    points: points.map(([px, py]) => `${px.toFixed(2)},${py.toFixed(2)}`)
      .join(" "),
    ...shaped,
  });
}


// -------------------------------------------------------------- trend
//
// `--list`, made visual. The question is "is this project drifting",
// and the answer is a shape.

export function renderTrend(store, schema = undefined) {
  const rows = store?.snapshots ?? [];
  if (rows.length < 2) return null;
  const markers = verdictMarkers(schema);

  const W = 100, H = 40;
  // UX-203: the axis is duration. It was `bytes`, so the trend
  // answered "is this project drifting" with disk usage.
  const sizes = rows.map((r) => r.total_duration_us ?? 0);
  const max = Math.max(...sizes, 1);
  const x = (i) => (rows.length === 1 ? W / 2 : (i / (rows.length - 1)) * W);
  const y = (v) => H - (v / max) * (H - 6) - 3;

  const figure = svg("svg", {
    viewBox: `0 0 ${W} ${H}`, class: "trend", preserveAspectRatio: "none",
    role: "img", "data-points": rows.length,
  });
  figure.append(svg("polyline", {
    points: rows.map((r, i) => `${x(i)},${y(r.total_duration_us ?? 0)}`).join(" "),
    class: "trend-line", fill: "none",
  }));
  for (const [index, row] of rows.entries()) {
    // Incomplete snapshots are *marked*, not hidden: they occupy the
    // disk, and a trend that quietly dropped them would answer the
    // drift question with a curated subset.
    const reason = row.incomplete_reason;
    // UX-203: the verdict colours the dot - the question the trend is
    // asked is whether this build is drifting, and the verdict is the
    // answer the rest of the tool already gives for one pair.
    const verdict = row.verdict_kind ?? "";
    const point = reason
      ? svg("rect", {
          x: x(index) - 1.3, y: y(row.total_duration_us ?? 0) - 1.3, width: 2.6,
          height: 2.6, class: "trend-point incomplete", "data-marker": "square",
          "data-stamp": row.stamp, "data-incomplete": reason })
      : markerPoint(verdictMarker(verdict, markers), x(index),
                    y(row.total_duration_us ?? 0), 1.3, {
          class: `trend-point${row.alias ? " aliased" : ""}`
                 + (verdict ? ` verdict-${verdict}` : ""),
          "data-stamp": row.stamp, "data-alias": row.alias ?? "",
          "data-verdict": verdict });
    // Size is still here, demoted to where it belongs: a detail you can
    // hover for, not the axis the question is answered on.
    const tip = svg("title");
    tip.textContent = [
      row.stamp,
      row.total_duration_us != null ? seconds(row.total_duration_us) : null,
      verdict ? verdict.replace(/_/g, " ") : null,
      row.cache_hit_rate != null
        ? `${(row.cache_hit_rate * 100).toFixed(0)}% cache hits` : null,
      row.bytes != null ? mib(row.bytes) : null,
    ].filter(Boolean).join(" · ");
    point.append(tip);
    figure.append(point);
  }

  const wrapper = document.createElement("section");
  wrapper.setAttribute("data-section", "store-trend");
  const heading = document.createElement("h2");
  heading.textContent = `The store (${rows.length} snapshots)`;
  // UX-209: the shape, then one line. The reasons stay behind a fold
  // rather than leaving the page - a reader who wants to know why a
  // square is a square is one click away, and a reader who does not is
  // no longer scrolling past it.
  const caption = document.createElement("p");
  caption.className = "muted";
  const incomplete = rows.filter((r) => r.incomplete_reason);
  caption.textContent = incomplete.length
    ? `${rows.length} snapshots \u00b7 ${incomplete.length} not measurements`
    : `${rows.length} snapshots \u00b7 all finished`;
  wrapper.append(heading, figure, caption);
  if (incomplete.length) {
    const why = document.createElement("details");
    why.className = "muted";
    why.setAttribute("data-fold", "trend-squares");
    const summary = document.createElement("summary");
    summary.textContent = "What the squares are";
    const body = document.createElement("p");
    body.textContent =
      "Snapshots that are not measurements ("
      + `${[...new Set(incomplete.map((r) => r.incomplete_reason))].join(", ")}`
      + "); they are on disk, so they are on the chart.";
    why.append(summary, body);
    wrapper.append(why);
  }
  return wrapper;
}

// ---------------------------------------------------------- blast box
//
// The search box is a *transport*: it hands the target to the server,
// which calls the same function `bga blast` calls. No resolution
// happens here, because a second resolver would be a second answer.

export function renderBlastSearch(onQuery) {
  const wrapper = document.createElement("section");
  wrapper.setAttribute("data-section", "blast");
  const heading = document.createElement("h2");
  heading.textContent = "What rebuilds if I touch this?";
  const form = document.createElement("form");
  form.setAttribute("data-role", "blast-form");
  const input = document.createElement("input");
  input.setAttribute("data-role", "blast-input");
  input.placeholder = "a git url, a path in the project, or an element name";
  input.size = 52;
  const button = document.createElement("button");
  button.textContent = "Ask";
  const answer = document.createElement("div");
  answer.setAttribute("data-role", "blast-answer");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    answer.textContent = "asking…";
    try {
      const result = await onQuery(input.value);
      answer.replaceChildren(renderBlastAnswer(result));
    } catch (error) {
      answer.textContent = String(error.message ?? error);
    }
  });
  form.append(input, button);
  wrapper.append(heading, form, answer);
  return wrapper;
}

/**
 * `UX-208` item 5: example chips, from the payload's own ranking.
 *
 * A search box with no examples is a box a reader has to already know
 * the answer to use. The chips are the top blast-radius elements the
 * report already published - not a guess, and absent when the ranking
 * is (an empty ranking means no chips, never invented ones).
 */
export function blastChips(payload, onPick, make) {
  const ranked = (payload?.signals?.top_blast_radius) || [];
  if (!ranked.length) return null;
  const row = make("p", { class: "blast-chips" });
  row.append(make("span", { class: "muted" }, "Try: "));
  for (const uid of ranked.slice(0, 4)) {
    const chip = make("button", { type: "button", class: "chip",
                                  "data-element": uid }, uid);
    chip.addEventListener?.("click", () => onPick(uid));
    row.append(chip);
  }
  return row;
}

export function renderBlastAnswer(result) {
  const list = document.createElement("dl");
  list.className = "pairs";
  list.setAttribute("data-role", "blast-result");
  // Straight from `blast/v1`; the sentence about keying is the payload's
  // own, so the page and `bga blast` cannot phrase it differently.
  const rows = [
    ["Resolved as", result.resolved_as],
    ["Keying", result.keying],
    ["Direct", result.direct_count],
    ["Rebuilds", result.blast_count],
    ["Of which build", result.building_count],
    ["…and assemble", result.assembling_count],
    ["Measured", result.measured
      ? `${result.measured_seconds?.toFixed?.(1) ?? result.measured_seconds}s `
        + `over ${result.measured_elements} element(s)`
      : "not measured (--no-cost, or no run)"],
  ];
  for (const [name, value] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = name;
    const dd = document.createElement("dd");
    dd.textContent = value === null || value === undefined ? "—" : String(value);
    dd.setAttribute("data-key", name.toLowerCase().replace(/\W+/g, "_"));
    list.append(dt, dd);
  }
  // UX-206: and the same answer as a tree, under the summary that
  // counts it. The counts say how much; the tree says what, and at what
  // remove.
  const tree = renderBlastTree(result);
  if (!tree) return list;
  const wrapper = document.createElement("div");
  wrapper.append(list, tree);
  return wrapper;
}

// ------------------------------------------------- UX-202: the overview
//
// "Why is my build slow" answered at the top, before the sections.
//
// **The rule this is built under: no viewer arithmetic.** Every number
// below is read from a published field and rendered; none is computed
// here. A gap the JSON does not carry enters `analyze/v1` first, where
// the text renderer, CI and every external consumer get it too - which
// is Direction 7's rule, and the reason the waterfall is a *reading* of
// the report rather than a second opinion about it.

// The waterfall, in the order the time is spent. Each entry names the
// published field it reads; nothing here adds, subtracts or divides.
const WATERFALL = [
  { key: "untracked_head_us", label: "Before the first task", from: "attribution" },
  { key: "execution_on_chain_us", label: "Execution on the chain", from: "attribution" },
  { key: "dependency_wait_us", label: "Waiting on dependencies", from: "attribution" },
  { key: "resource_wait_us", label: "Waiting on resources", from: "attribution" },
  { key: "scheduler_wait_us", label: "Waiting on the scheduler", from: "attribution" },
  { key: "retry_wait_us", label: "Retries", from: "attribution" },
  { key: "idle_us", label: "Idle", from: "attribution" },
  { key: "untracked_tail_us", label: "After the last task", from: "attribution" },
];

// The certified floors, read the same way.
const FLOORS = [
  { key: "t_infinity_observed", label: "T∞ (observed)" },
  { key: "lb", label: "LB" },
  { key: "t_c", label: "T_C" },
  { key: "certified_headroom", label: "Certified headroom" },
];

function bar(label, value, total, extra = {}) {
  const row = document.createElement("div");
  row.className = "wf-row";
  for (const [name, attr] of Object.entries(extra)) row.setAttribute(name, attr);
  const name = document.createElement("span");
  name.className = "wf-label";
  name.textContent = label;
  const track = document.createElement("span");
  track.className = "wf-track";
  const fill = document.createElement("span");
  fill.className = "wf-fill";
  // The only division in this file, and it is a *width*, not a number
  // the reader is told: the printed value is `value` itself.
  fill.setAttribute("style",
    `width: ${total > 0 ? Math.max(0, Math.min(100, (value / total) * 100)) : 0}%`);
  track.append(fill);
  const amount = document.createElement("span");
  amount.className = "wf-value num";
  amount.setAttribute("data-raw", String(value));
  amount.textContent = seconds(value);
  row.append(name, track, amount);
  return row;
}

export function renderOverview(payload) {
  const total = payload?.total_duration_us;
  const attribution = payload?.attribution;
  if (typeof total !== "number" || !attribution) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "overview");
  section.setAttribute("id", "overview");
  const heading = document.createElement("h2");
  heading.textContent = "Where the time went";
  section.append(heading);

  section.append(bar("Total duration", total, total,
                     { "data-field": "total_duration_us" }));

  // UX-207: the largest segments stay visible and the tail folds -
  // **with no viewer-summed "Other" row.** A grouped figure would be a
  // number the pipeline never published, which is the one thing this
  // drawing is not allowed to invent. Ordering is by published value;
  // the fold hides rows, it does not merge them.
  const drawn = WATERFALL
    .map((entry) => ({ entry, value: attribution[entry.key] }))
    .filter((row) => typeof row.value === "number" && row.value !== 0)
    .sort((a, b) => b.value - a.value);
  const head = drawn.slice(0, OVERVIEW_SHOWN);
  const tail = drawn.slice(OVERVIEW_SHOWN);
  const segment = (row) => bar(row.entry.label, row.value, total, {
    "data-field": `attribution.${row.entry.key}`,
    // UX-199's anchors: each segment points at the section that
    // explains it.
    "data-section-link": "attribution",
  });
  for (const row of head) section.append(segment(row));
  if (tail.length) {
    const fold = document.createElement("details");
    fold.className = "overview-tail";
    fold.setAttribute("data-folded", String(tail.length));
    fold.setAttribute("data-fold", "overview-tail");
    const summary = document.createElement("summary");
    summary.textContent = `${tail.length} smaller categories`;
    fold.append(summary);
    for (const row of tail) fold.append(segment(row));
    section.append(fold);
  }

  const floors = payload?.floors;
  if (floors) {
    const sub = document.createElement("h3");
    sub.textContent = "And the floors underneath it";
    section.append(sub);
    for (const entry of FLOORS) {
      const value = floors[entry.key];
      if (typeof value !== "number") continue;
      section.append(bar(entry.label, value, total, {
        "data-field": `floors.${entry.key}`,
        "data-section-link": "floors",
      }));
    }
  }
  return section;
}

/**
 * What this capture can support, before any number is believed.
 *
 * `UX-156`'s tone, and the place the refusal banners belong: an
 * interrupted or suspended run says so here rather than floating above
 * a report that looks otherwise ordinary.
 */
export function renderEvidence(payload) {
  const confidence = payload?.confidence ?? {};
  const instance = payload?.run_instance ?? {};
  const host = instance.host_manifest ?? {};
  const reason = instance.incomplete_reason;

  const rows = [];
  if (typeof confidence.primary === "number") {
    rows.push(["Confidence",
               `${(confidence.primary * 100).toFixed(0)}%`
               + (confidence.band ? ` (${confidence.band})` : ""),
               "confidence.primary"]);
  }
  if (typeof confidence.task_coverage === "number") {
    rows.push(["Task coverage",
               `${(confidence.task_coverage * 100).toFixed(0)}%`,
               "confidence.task_coverage"]);
  }
  // UX-202: Plane 2's half of "what can this capture support". Absent
  // when `analyze` had no Plane 2 report - and absent is the honest
  // rendering: a "0%" row would claim the hook saw nothing, when the
  // truth is that nobody looked.
  const plane2 = payload?.plane2_coverage;
  if (plane2 && typeof plane2.processes === "number") {
    rows.push(["Plane 2 coverage",
               `${plane2.processes} processes`
               + (typeof plane2.opens_coverage === "number"
                  ? `, opens ${(plane2.opens_coverage * 100).toFixed(0)}%` : ""),
               "plane2_coverage.processes"]);
  }
  if (host.cpu_model) {
    rows.push(["Host",
               [host.cpu_model, host.cpu_count && `${host.cpu_count} cpu`,
                host.memory_mb && `${Math.round(host.memory_mb / 1024)} GiB`]
                 .filter(Boolean).join(" · "),
               "run_instance.host_manifest"]);
  }
  if (instance.started_at) {
    rows.push(["Captured", instance.started_at, "run_instance.started_at"]);
  }
  if (!rows.length && !reason) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "evidence");
  section.setAttribute("id", "evidence");
  const heading = document.createElement("h2");
  heading.textContent = "What this capture supports";
  section.append(heading);

  // UX-207: **the refusal renders once.** It used to appear here *and*
  // in `renderVerdict`, the same sentence in two banners - measured at
  // two `data-incomplete` nodes on an interrupted fixture. The banner
  // belongs above the decision, not inside a header a reader may have
  // collapsed, so `renderVerdict` keeps it and this stops drawing it.
  //
  // Everything else here compresses to one line: six rows at the top of
  // a page for values that matter only when they are alarming.
  const status = document.createElement("p");
  status.className = "status-line";
  status.setAttribute("data-role", "status");
  status.textContent = statusLine(payload);
  section.append(status);

  const fold = document.createElement("details");
  fold.className = "evidence-detail";
  fold.setAttribute("data-fold", "evidence");
  const summary = document.createElement("summary");
  summary.textContent = "The numbers behind that";
  fold.append(summary);

  const list = document.createElement("dl");
  list.className = "pairs";
  for (const [label, value, field] of rows) {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.setAttribute("data-field", field);
    detail.textContent = value;
    list.append(term, detail);
  }
  fold.append(list);
  section.append(fold);
  return section;
}

/**
 * `✓ high confidence · 100% task coverage · Plane 2 available`
 *
 * Every part read from a published field; a part with no field is
 * simply not said. The tick is the *band*, which `findings.py` decides
 * - the page does not get to call 0.87 high.
 */
export function statusLine(payload) {
  const confidence = payload?.confidence ?? {};
  const parts = [];
  if (confidence.band) {
    const mark = confidence.band === "high" ? "\u2713"
      : confidence.band === "low" ? "\u26a0" : "\u00b7";
    parts.push(`${mark} ${confidence.band} confidence`);
  } else if (typeof confidence.primary === "number") {
    parts.push(`confidence ${(confidence.primary * 100).toFixed(0)}%`);
  }
  if (typeof confidence.task_coverage === "number") {
    parts.push(`${(confidence.task_coverage * 100).toFixed(0)}% task coverage`);
  }
  const plane2 = payload?.plane2_coverage;
  parts.push(plane2 && typeof plane2.processes === "number"
    ? `Plane 2: ${plane2.processes} processes`
    : "Plane 2 not captured");
  return parts.join(" \u00b7 ");
}

// The same three sentences the CLI banners use. One source, so the
// page and the terminal cannot describe the same run differently.
export const INCOMPLETE = {
  failed: "This build failed: durations from a run that did not finish "
          + "are not measurements.",
  interrupted: "This capture was interrupted: durations from a run that did "
               + "not finish are not measurements.",
  suspended: "This capture spans a suspend: Plane 1 counts the sleep as "
             + "build time and Plane 2 does not, so the durations here are "
             + "not measurements.",
};


// ------------------------------------------------- UX-206: two graphs

// No general DAG viewer. The external review and Direction 7 arrived at
// that restraint independently: a BuildStream DAG rendering answers no
// question anyone asks, and the temptation to build one loses to the
// two drawings that *are* questions. Neither needs a layout algorithm -
// one is a list with widths, the other is an indented list.

/** How many of the chain's elements are drawn before the fold. */
// UX-207: how many attribution bars stay unfolded.
const OVERVIEW_SHOWN = 4;

const PATH_HEAD = 6;
const PATH_TAIL = 3;

/**
 * The critical path, drawn: the chain the report already prints as
 * text, as a sequence of boxes sized by their published share.
 *
 * `share_of_path` is a *published field*, so no width here is computed
 * from a duration - the same rule the overview waterfall follows, and
 * the reason the geometry can be asserted from the payload.
 *
 * `UX-187`'s fold, expandable in place: a 1,202-element chain is not a
 * drawing, and the middle is where a reader stops looking anyway.
 */
export function renderCriticalPath(payload) {
  const detail = payload?.signals?.critical_path_detail;
  if (!Array.isArray(detail) || !detail.length) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "critical-path-drawn");
  section.setAttribute("id", "critical-path-drawn");
  const heading = document.createElement("h2");
  heading.textContent = "The chain, drawn";
  section.append(heading);

  const strip = document.createElement("div");
  strip.className = "path-strip";
  strip.setAttribute("data-elements", String(detail.length));

  const folded = detail.length > PATH_HEAD + PATH_TAIL + 1;
  const head = folded ? detail.slice(0, PATH_HEAD) : detail;
  const tail = folded ? detail.slice(detail.length - PATH_TAIL) : [];
  const middle = folded ? detail.slice(PATH_HEAD, detail.length - PATH_TAIL) : [];

  for (const entry of head) strip.append(pathBox(entry));
  if (folded) {
    const hidden = [];
    for (const entry of middle) {
      const box = pathBox(entry);
      box.hidden = true;
      hidden.push(box);
      strip.append(box);
    }
    const more = document.createElement("button");
    more.className = "path-more";
    more.setAttribute("type", "button");
    more.setAttribute("data-folded", String(middle.length));
    more.textContent = `+${middle.length} more`;
    // In place: the fold opens between the two ends rather than
    // scrolling the reader somewhere else.
    more.addEventListener("click", () => {
      for (const box of hidden) box.hidden = false;
      more.hidden = true;
    });
    strip.append(more);
  }
  for (const entry of tail) strip.append(pathBox(entry));
  section.append(strip);
  return section;
}

function pathBox(entry) {
  const box = document.createElement("a");
  box.className = "path-box";
  box.setAttribute("data-element", entry.element_uid ?? "");
  box.setAttribute("data-share", String(entry.share_of_path ?? 0));
  box.setAttribute("data-duration-us", String(entry.duration_us ?? 0));
  // The width is the published share, read not computed. `min-width`
  // in the stylesheet keeps a 0.1% element clickable.
  box.setAttribute("style",
    `flex-grow: ${Math.max(0, Number(entry.share_of_path) || 0) * 1000}`);
  // UX-199's anchors: the drawing points back at the section that
  // explains it. UX-216: and that is now the *element's* section
  // rather than the whole signals block - a reader who clicks a box
  // asked about that element, not about the table it came from.
  box.setAttribute("href", `#${elementAnchor(entry.element_uid ?? "")}`);
  const name = document.createElement("span");
  name.className = "path-name";
  name.textContent = entry.element_uid ?? "";
  const time = document.createElement("span");
  time.className = "path-time num";
  time.textContent = seconds(entry.duration_us ?? 0);
  box.append(name, time);

  // UX-208 item 1: the popover, read from the published entry. Every
  // line here is a field - there is no fixture on which a recomputed
  // share would pass, which is what the acceptance asks for.
  const detail = [
    entry.element_uid,
    typeof entry.duration_us === "number" ? seconds(entry.duration_us) : null,
    typeof entry.share_of_path === "number"
      ? `${(entry.share_of_path * 100).toFixed(1)}% of the path` : null,
    entry.element_kind ? `kind: ${entry.element_kind}` : null,
    typeof entry.realizable_saving_us === "number"
      ? `fixing it saves ${seconds(entry.realizable_saving_us)}` : null,
  ].filter(Boolean).join(" \u00b7 ");
  box.setAttribute("title", detail);
  box.setAttribute("data-popover", detail);
  if (entry.element_kind) {
    const badge = document.createElement("span");
    badge.className = "kind";
    badge.textContent = entry.element_kind;
    box.append(badge);
  }
  return box;
}

/**
 * The blast answer as an indented hierarchy: direct consumers, then the
 * closure by depth, each row with its kind badge and measured work.
 *
 * `blast_tree` is the payload `UX-206` assumed `blast/v1` already
 * carried and it did not - the answer had two flat lists and no depth
 * at all, and depth is the whole shape of a tree. It is published now
 * (`bga/blast.py`), so this reads rather than walks a graph.
 */
export function renderBlastTree(payload) {
  const tree = payload?.blast_tree;
  if (!Array.isArray(tree) || !tree.length) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "blast-tree");
  section.setAttribute("id", "blast-tree");
  const heading = document.createElement("h2");
  heading.textContent = `What a change to ${payload.target ?? "it"} rebuilds`;
  section.append(heading);

  const list = document.createElement("div");
  list.className = "blast-tree";
  for (const entry of tree) {
    const depth = Number(entry.depth) || 0;
    const row = document.createElement("div");
    row.className = "blast-row";
    row.setAttribute("data-element", entry.element_uid ?? "");
    row.setAttribute("data-depth", String(depth));
    // Indentation is the published depth, not a position in the list.
    row.setAttribute("style", `padding-left: ${depth * 1.4}rem`);
    // UX-216: the blast tree names elements; each is a link to the
    // element's own section where it has one.
    const name = document.createElement("a");
    name.className = "blast-name";
    name.setAttribute("href", `#${elementAnchor(entry.element_uid ?? "")}`);
    name.textContent = entry.element_uid ?? "";
    row.append(name);
    if (entry.element_kind) {
      const badge = document.createElement("span");
      badge.className = "kind";
      badge.setAttribute("data-kind", entry.element_kind);
      badge.textContent = entry.element_kind;
      row.append(badge);
    }
    if (typeof entry.measured_seconds === "number") {
      const cost = document.createElement("span");
      cost.className = "blast-cost num";
      cost.setAttribute("data-raw", String(entry.measured_seconds));
      cost.textContent = seconds(entry.measured_seconds * 1e6);
      row.append(cost);
    }
    list.append(row);
  }
  section.append(list);
  return section;
}


// ------------------------------------------------- UX-207: the decision

/**
 * The first screen, and the only one that is not evidence.
 *
 * **Everything here is read.** The diagnosis, the ratio it came from,
 * the opportunity split and the ranked actions are all fields of the
 * published `headline` block - `UX-207`'s rule, and Direction 7's: a
 * viewer that derives the diagnosis is a second analyzer, free to
 * disagree with the report and the CI gate about the same build.
 *
 * No `headline`, no panel. An older payload renders the page it always
 * did rather than a box explaining what is missing.
 */
export function renderDecision(payload, investigate = null, copy = null) {
  const headline = payload?.headline;
  if (!headline || !headline.diagnosis) return null;

  const section = document.createElement("section");
  section.className = "decision";
  section.setAttribute("data-section", "decision");
  section.setAttribute("id", "decision");
  section.setAttribute("data-diagnosis", headline.diagnosis);

  const heading = document.createElement("h2");
  heading.textContent = "What to fix first";
  section.append(heading);

  const sentence = document.createElement("p");
  sentence.className = "diagnosis";
  sentence.setAttribute("data-field", "headline.sentence");
  sentence.textContent = headline.sentence ?? "";
  section.append(sentence);

  // The opportunity split, both halves published. Absent stays absent -
  // a zero here would claim a measurement nobody made.
  const split = document.createElement("dl");
  split.className = "pairs opportunity";
  for (const [label, key, kind] of [
    ["Certified headroom", "certified_headroom_us", "duration_us"],
    ["Beyond the chain", "scheduling_gap_us", "duration_us"],
  ]) {
    const value = headline[key];
    if (typeof value !== "number") continue;
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.className = "num";
    detail.setAttribute("data-field", `headline.${key}`);
    detail.setAttribute("data-raw", String(value));
    detail.textContent = kind === "duration_us" ? seconds(value) : String(value);
    split.append(term, detail);
  }
  if (split.children?.length) section.append(split);

  const actions = Array.isArray(headline.top_actions) ? headline.top_actions : [];
  if (actions.length) {
    const list = document.createElement("ol");
    list.className = "actions";
    for (const action of actions) {
      list.append(actionRow(action, investigate));
    }
    section.append(list);
  }

  // UX-218: and what to run next. Read from `next_steps`, never
  // derived - the branch that chose these lives in the pipeline, so
  // the terminal, CI and this panel give the same answer.
  const steps = Array.isArray(payload?.next_steps) ? payload.next_steps : [];
  if (steps.length) {
    const heading = document.createElement("h3");
    heading.textContent = "Next";
    section.append(heading);
    const list = document.createElement("ol");
    list.className = "next-steps";
    for (const step of steps) list.append(nextStepRow(step, copy));
    section.append(list);
  }
  return section;
}

/**
 * One published next step: why, and the exact command.
 *
 * `copy` is passed in rather than imported so this file keeps having
 * no dependency on `tables.js` - and so a harness can drive the button
 * without a clipboard.
 */
function nextStepRow(step, copy) {
  const row = document.createElement("li");
  row.className = "next-step";
  row.setAttribute("data-step", step.id ?? "");
  row.setAttribute("data-follows-from", step.follows_from ?? "");

  const why = document.createElement("p");
  why.className = "muted";
  why.textContent = step.reason ?? "";
  row.append(why);

  const argv = Array.isArray(step.argv) ? step.argv.join(" ") : "";
  const command = document.createElement("code");
  command.className = "next-command";
  command.setAttribute("data-argv", argv);
  command.textContent = argv;
  row.append(command);

  if (copy && argv) {
    const button = document.createElement("button");
    button.setAttribute("type", "button");
    button.className = "copy-step";
    button.textContent = "Copy";
    button.addEventListener("click", () => {
      copy(argv);
      button.textContent = "\u2713 copied";
      setTimeout(() => { button.textContent = "Copy"; }, 1200);
    });
    row.append(button);
  }
  return row;
}

function actionRow(action, investigate) {
  const row = document.createElement("li");
  row.className = "action";
  row.setAttribute("data-element", action.element_uid ?? "");
  row.setAttribute("data-finding", action.finding_id ?? "");

  // UX-216: the decision panel names an element; naming it and not
  // linking it is the gap this item closes.
  const name = document.createElement("a");
  name.setAttribute("href", `#${elementAnchor(action.element_uid ?? "")}`);
  const code = document.createElement("code");
  code.textContent = action.element_uid ?? "";
  name.append(code);
  row.append(name);

  if (typeof action.saving_us === "number") {
    const worth = document.createElement("span");
    worth.className = "worth num";
    worth.setAttribute("data-field", "saving_us");
    worth.setAttribute("data-raw", String(action.saving_us));
    worth.textContent = `saves ${seconds(action.saving_us)}`;
    row.append(worth);
  } else if (typeof action.downstream_count === "number") {
    const reach = document.createElement("span");
    reach.className = "worth num";
    reach.setAttribute("data-field", "downstream_count");
    reach.setAttribute("data-raw", String(action.downstream_count));
    reach.textContent = `${action.downstream_count} downstream`;
    row.append(reach);
  }

  // The reasoning is a section away, not restated here - `finding_id`
  // is a reference for exactly this.
  const why = document.createElement("a");
  why.className = "why";
  why.setAttribute("href", "#findings");
  why.textContent = "why";
  row.append(why);

  // UX-204's transport, where there is a timeline behind it.
  if (investigate) {
    const button = investigate(action);
    if (button) row.append(button);
  }
  return row;
}

// -------------------------------------------------- the element object
//
// UX-216. An element uid appears in findings, the critical path, three
// signals tables, the blast tree, the top actions and (since UX-215)
// the two-plane join. A reader who wants "everything about core.bst"
// reads six sections and joins them by hand.
//
// And UX-208 shipped the affordance for exactly this and pointed it at
// nothing: every row's Inspect anchored at `#element-<uid>`, an id
// nothing in the page ever set. Measured on examples/06 before this
// landed: 19 links, 11 distinct targets, 11 of 11 unresolvable. This
// is what they land on, which is why the fix and the object are one
// change rather than two.
//
// Deliberately a *section*, not a drawer. Overlay machinery is the one
// part of this page that would not survive an export opened from a
// downloads folder, a print, `filter: grayscale`, or a pasted anchor -
// and a section is linkable, printable, collapsible and foldable by
// machinery that already exists.

// How many element sections a report renders. The set below is already
// bounded by the analysis (a path, a top-N, a findings list), but a
// 4,000-element report can still produce a long path, and UX-187's rule
// is that an elision names its own count.
export const ELEMENTS_SHOWN = 24;

/** The element uid an anchor fragment is spelled as. Mirrors
 *  `app.js`'s `cssId` - the two are asserted equal by a guard, because
 *  a link and its target spelling drifting apart is this item. */
export function elementAnchor(uid) {
  return `element-${String(uid).replace(/[^\w-]+/g, "-")}`;
}

/**
 * Everything the payload says about each element it discusses.
 *
 * Published fields only, and no arithmetic: a value that is not in the
 * document does not appear here. The order is the report's own ranking
 * - top actions first, then the path, then the horizon - so the
 * sections a reader meets first are the ones the decision named.
 */
export function elementFacts(payload) {
  const facts = new Map();
  const touch = (uid) => {
    if (!uid) return null;
    if (!facts.has(uid)) {
      facts.set(uid, { element: uid, rows: [], findings: [], entering: [] });
    }
    return facts.get(uid);
  };

  // Where each fact comes from, declared rather than repeated: the
  // published array, the key that names the element in it, and the
  // fields worth showing with the quantity each is in. Adding a field
  // is a line here, and no new code.
  for (const [array, idKey, fields] of SOURCES) {
    const rows = array.split(".").reduce((node, key) => node?.[key], payload);
    for (const entry of rows ?? []) {
      const record = facts.has(entry[idKey]) || array !== "element_join"
        ? touch(entry[idKey]) : null;      // the join follows, never leads
      if (!record) continue;
      for (const [field, label, kind] of fields) {
        const value = entry[field];
        if (value !== null && value !== undefined) {
          record.rows.push({ label, value, kind, field });
        }
      }
      if (Array.isArray(entry.entering) && entry.entering.length) {
        record.entering = entry.entering;
      }
    }
  }
  for (const finding of payload?.findings ?? []) {
    for (const uid of finding.elements ?? []) {
      const record = facts.get(uid);
      if (record) record.findings.push(finding);
    }
  }
  return facts;
}

// The report's own ranking decides the order: what the decision named
// first, then the path, then the horizon. `element_join` (UX-215) is
// last and never introduces an element - it is the Plane 2 half of
// elements Plane 1 already put in play, which is what lets the section
// answer "compute-bound, or badly built".
const SOURCES = [
  ["headline.top_actions", "element_uid", [
    ["saving_us", "Worth fixing", "duration_us"],
    ["downstream_count", "Rebuilds", "count"]]],
  ["signals.critical_path_detail", "element_uid", [
    ["share_of_path", "Share of path", "share"],
    ["duration_us", "Duration", "duration_us"],
    ["realizable_saving_us", "Realizable", "duration_us"],
    ["element_kind", "Kind", null]]],
  ["signals.optimization_horizon", "element_uid", [
    ["makespan_after_us", "Makespan after", "duration_us"]]],
  ["signals.latent_heavies", "element_uid", [
    ["duration_us", "Duration", "duration_us"]]],
  ["element_join", "element", [
    ["cores_busy", "Cores busy", "ratio"],
    ["requested_jobs", "Jobs asked for", "count"],
    ["peak_rss_kb", "Peak RSS", "kilobytes"],
    ["blast_radius", "Blast radius", "count"]]],
];

/**
 * One section per element the report discusses.
 *
 * `where` is the cross-reference and it is read off the *rendered
 * document* rather than from the payload: whatever else the page drew
 * with a `data-element`, the section links back to the part of the page
 * that drew it. So a section added later joins this list with no edit
 * here - the property `UX-193` bought for the sections themselves.
 */
export function renderElementSections(payload, root, options = {}) {
  const { investigate = null, quantity: format = (v) => String(v) } = options;
  const facts = elementFacts(payload);
  if (!facts.size) return [];

  const places = new Map();
  for (const node of root?.querySelectorAll?.("[data-element]") ?? []) {
    const uid = node.getAttribute("data-element");
    if (!uid || !facts.has(uid)) continue;
    let owner = node.parentNode;
    while (owner && !owner.getAttribute?.("data-section")) {
      owner = owner.parentNode;
    }
    const key = owner?.getAttribute?.("data-section");
    if (!key || key.startsWith("element-")) continue;
    if (!places.has(uid)) places.set(uid, new Set());
    places.get(uid).add(key);
  }

  const sections = [];
  const all = [...facts.values()];
  for (const record of all.slice(0, ELEMENTS_SHOWN)) {
    sections.push(elementSection(record, places.get(record.element),
                                 investigate, format));
  }
  if (all.length > ELEMENTS_SHOWN) {
    // UX-187: an elision names its count and never pretends to be the
    // whole list.
    const note = document.createElement("p");
    note.className = "muted";
    note.setAttribute("data-elided", String(all.length - ELEMENTS_SHOWN));
    note.textContent =
      `${all.length - ELEMENTS_SHOWN} more elements are named in the tables `
      + `above and do not have their own section.`;
    sections.push(note);
  }
  return sections;
}

function elementSection(record, places, investigate, format) {
  const uid = record.element;
  const section = document.createElement("section");
  // `UX-199`'s invariant is that a section's id *is* its key, and this
  // one is the sanitised spelling because a dot in an id is legal and
  // awkward in a selector - so the key is the sanitised spelling too,
  // rather than the two being nearly the same and drifting.
  section.setAttribute("data-section", elementAnchor(uid));
  section.setAttribute("data-element", uid);
  // The id UX-208's anchors have been pointing at since round 23.
  section.setAttribute("id", elementAnchor(uid));
  // ...and the uid is what the contents should say, not the sanitised
  // key mechanically de-hyphenated into "Element core bst".
  section.setAttribute("data-toc-label", uid);
  section.setAttribute("data-rail", "investigate");

  const heading = document.createElement("h2");
  heading.textContent = uid;
  section.append(heading);

  // UX-222 and UX-225: the two controls that act on *this* element.
  // Plain buttons carrying the element and the intent - `app.js` wires
  // one delegated listener at the root, so a control added to a view
  // later needs no second handler.
  const controls = document.createElement("p");
  controls.className = "element-controls";
  controls.setAttribute("data-role", "element-controls");
  const focusButton = document.createElement("button");
  focusButton.setAttribute("type", "button");
  focusButton.className = "focus-this";
  focusButton.setAttribute("data-focus-element", uid);
  focusButton.textContent = "Focus";
  controls.append(focusButton);
  for (const mark of ELEMENT_MARKS) {
    const button = document.createElement("button");
    button.setAttribute("type", "button");
    button.className = "mark-this";
    button.setAttribute("data-mark-element", uid);
    button.setAttribute("data-mark-value", mark);
    button.textContent = ELEMENT_MARK_LABELS[mark];
    controls.append(button);
  }
  section.append(controls);

  if (record.rows.length) {
    const list = document.createElement("dl");
    list.className = "pairs";
    for (const row of record.rows) {
      const term = document.createElement("dt");
      term.textContent = row.label;
      const detail = document.createElement("dd");
      detail.setAttribute("data-field", row.field);
      detail.setAttribute("data-raw", String(row.value));
      detail.className = typeof row.value === "number" ? "num" : "";
      detail.textContent = typeof row.value === "number"
        ? format(row.value, row.kind) : String(row.value);
      list.append(term, detail);
    }
    section.append(list);
  }

  if (record.entering.length) {
    const enters = document.createElement("p");
    enters.className = "muted";
    enters.setAttribute("data-entering", record.entering.join(","));
    enters.textContent =
      `Fixing this puts ${record.entering.join(", ")} on the critical path.`;
    section.append(enters);
  }

  for (const finding of record.findings) {
    const line = document.createElement("p");
    line.className = `finding-ref sev-${String(finding.severity ?? "info")
      .toLowerCase()}`;
    line.setAttribute("data-finding", finding.id ?? "");
    line.textContent = finding.title ?? finding.id ?? "";
    section.append(line);
  }

  if (places && places.size) {
    const where = document.createElement("p");
    where.className = "where muted";
    where.append(document.createTextNode("Also in: "));
    for (const key of [...places].sort()) {
      const link = document.createElement("a");
      link.setAttribute("href", `#${key}`);
      link.setAttribute("data-where", key);
      link.textContent = key.replace(/[-_]/g, " ");
      where.append(link, document.createTextNode(" "));
    }
    section.append(where);
  }

  if (investigate) {
    const button = investigate(uid);
    if (button) section.append(button);
  }
  return section;
}

// UX-221: the strip that answers "because of what?".
//
// `renderBand` says the candidate is outside the noise band. It cannot
// say which elements put it there, because until UX-221 the payload had
// no per-element deltas to say it with - `compare/v1` carried whole-run
// floors and per-*category* attribution, and the only elements in it at
// all were the ones a change added or removed.
//
// Read straight off `element_deltas.rows`, in the order the payload
// ranked them. A viewer sorting these itself would be a second
// comparison, disagreeing with `bga compare` the moment either changed -
// UX-214's failure, and the reason this was a payload item first.
export const CULPRITS_SHOWN = 4;

// UX-225's vocabulary, spelled here so `views.js` keeps importing
// nothing. A guard asserts it is the same closed set `focus.js`
// declares, so the two cannot drift apart in silence.
export const ELEMENT_MARKS = ["working", "done", "aside"];
export const ELEMENT_MARK_LABELS = {
  working: "Working", done: "Done", aside: "Set aside",
};

export function renderCulprits(compare) {
  const deltas = compare?.element_deltas;
  const rows = deltas?.rows ?? [];
  if (!rows.length) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "culprits");
  section.setAttribute("data-toc-label", "Which elements changed");
  const heading = document.createElement("h2");
  heading.textContent = "Which elements changed";
  section.append(heading);

  // Improvements and regressions each on their own, rather than one
  // list ordered by magnitude: a reader looking for what cost them time
  // should not have to skip past what saved it.
  const measurable = rows.filter((row) => row.delta_us !== null
                                       && row.delta_us !== undefined);
  const worse = measurable.filter((row) => row.delta_us > 0)
                          .slice(0, CULPRITS_SHOWN);
  const better = measurable.filter((row) => row.delta_us < 0)
                           .slice(0, CULPRITS_SHOWN);
  const absent = rows.filter((row) => row.presence !== "both");

  for (const [label, group] of [["Cost time", worse], ["Saved time", better]]) {
    if (!group.length) continue;
    const list = document.createElement("ul");
    list.className = "culprit-list";
    list.setAttribute("data-group", label === "Cost time" ? "worse" : "better");
    for (const row of group) list.append(culpritRow(row));
    const title = document.createElement("h3");
    title.textContent = label;
    section.append(title, list);
  }

  if (absent.length) {
    const list = document.createElement("ul");
    list.className = "culprit-list";
    list.setAttribute("data-group", "absent");
    for (const row of absent.slice(0, CULPRITS_SHOWN)) list.append(culpritRow(row));
    const title = document.createElement("h3");
    title.textContent = "Only in one run";
    section.append(title, list);
  }

  // The honesty line. A per-element delta is not judged against a noise
  // band - there isn't one - and a strip that coloured rows without
  // saying so would be claiming a verdict it cannot support.
  const caveat = document.createElement("p");
  caveat.className = "muted";
  caveat.setAttribute("data-role", "not-banded");
  caveat.textContent = deltas.banded
    ? "Each row is judged against its own noise band."
    : "These are raw changes, not judged against a noise band - only the "
      + "run as a whole is.";
  section.append(caveat);
  return section;
}

function culpritRow(row) {
  const item = document.createElement("li");
  item.setAttribute("data-element", row.element_uid);
  item.setAttribute("data-verdict-kind", row.verdict_kind);
  item.setAttribute("data-presence", row.presence);
  if (row.delta_us !== null && row.delta_us !== undefined) {
    item.setAttribute("data-delta-us", String(row.delta_us));
  }
  const name = document.createElement("a");
  name.className = "element";
  name.setAttribute("href", `#${elementAnchor(row.element_uid ?? "")}`);
  name.textContent = row.element_uid;
  const change = document.createElement("span");
  change.className = "culprit-change";
  // The values are the payload's. Nothing here subtracts anything: a
  // page computing its own delta is a second comparison.
  change.textContent = (row.delta_us === null || row.delta_us === undefined)
    ? `${row.presence} - no delta to compare`
    : `${row.delta_us > 0 ? "+" : ""}${seconds(row.delta_us)}`
      + ` (${seconds(row.baseline_us)} → ${seconds(row.candidate_us)})`;
  item.append(name, document.createTextNode(" "), change);
  return item;
}

// UX-219: the horizon, drawn.
//
// `signals.optimization_horizon` has carried the whole answer, per step,
// since long before this: the saving, the makespan that remains, and -
// the part a table hides - which elements *enter* the critical path once
// that step is taken. That is the honest reason the savings stop adding
// up, and it is what makes this a plan rather than a sum.
//
// Every width is one published `makespan_after_us` over one published
// total. Nothing here adds savings together or projects anything: if the
// payload publishes three steps, the plan has three rows.
export function renderHorizon(payload) {
  const steps = payload?.signals?.optimization_horizon ?? [];
  const total = payload?.total_duration_us;
  if (!steps.length || !total) return null;

  const section = document.createElement("section");
  section.setAttribute("data-section", "horizon");
  section.setAttribute("data-toc-label", "What if I fix these");
  section.setAttribute("data-total-us", String(total));
  const heading = document.createElement("h2");
  heading.textContent = "What if I fix these";
  section.append(heading);

  const list = document.createElement("ol");
  list.className = "horizon";

  // The run as it stands, so the bars below have something to shorten.
  list.append(horizonRow({
    label: "now", makespanUs: total, total,
    element: null, saving: null, entering: [],
  }));

  let taken = [];
  for (const step of steps) {
    taken = taken.concat([step.element_uid]);
    list.append(horizonRow({
      label: taken.length === 1
        ? `fix ${step.element_uid}`
        : `+ fix ${step.element_uid}`,
      makespanUs: step.makespan_after_us,
      total,
      element: step.element_uid,
      saving: step.saving_us,
      entering: step.entering ?? [],
    }));
  }
  section.append(list);

  // The total, from the last step's own published cumulative saving.
  // Not a sum computed here - the payload already decided what the
  // sequence is worth, and re-adding it would be a second answer.
  const last = steps[steps.length - 1];
  const cumulative = last?.cumulative_saving_us;
  if (cumulative !== null && cumulative !== undefined) {
    const summary = document.createElement("p");
    summary.className = "horizon-total";
    summary.setAttribute("data-role", "horizon-total");
    summary.setAttribute("data-cumulative-saving-us", String(cumulative));
    summary.setAttribute("data-total-us", String(total));
    const share = (cumulative / total) * 100;
    summary.textContent =
      `${steps.length} ${steps.length === 1 ? "fix" : "fixes"}`
      + ` → ${share.toFixed(0)}% faster (${seconds(cumulative)} off ${seconds(total)})`;
    section.append(summary);
  }
  return section;
}

function horizonRow({ label, makespanUs, total, element, saving, entering }) {
  const row = document.createElement("li");
  row.className = "horizon-step";
  // The published value, on the element, so a guard can check the
  // drawing against the payload without reading computed style.
  row.setAttribute("data-makespan-after-us", String(makespanUs));
  if (element) row.setAttribute("data-element", element);
  if (saving !== null && saving !== undefined) {
    row.setAttribute("data-saving-us", String(saving));
  }

  const name = document.createElement("span");
  name.className = "horizon-label";
  if (element) {
    const link = document.createElement("a");
    link.className = "element";
    link.setAttribute("href", `#${elementAnchor(element)}`);
    link.textContent = element;
    name.append(document.createTextNode(label.startsWith("+") ? "+ fix " : "fix "),
                link);
  } else {
    name.textContent = label;
  }

  const bar = document.createElement("span");
  bar.className = "horizon-bar";
  bar.setAttribute("data-role", "bar");
  // One division, UX-202's rule: a proportion of a published total, not
  // a quantity derived in the page.
  bar.setAttribute("style", `--w: ${(makespanUs / total) * 100}%`);

  const value = document.createElement("span");
  value.className = "horizon-value";
  value.textContent = seconds(makespanUs);

  row.append(name, bar, value);

  // What joins the critical path once this step is taken. The reason
  // the savings stop adding up, and the reason this is a plan.
  if (entering.length) {
    const note = document.createElement("span");
    note.className = "horizon-entering muted";
    note.setAttribute("data-role", "entering");
    note.append(document.createTextNode("→ "));
    entering.forEach((uid, i) => {
      if (i) note.append(document.createTextNode(", "));
      const link = document.createElement("a");
      link.className = "element";
      link.setAttribute("href", `#${elementAnchor(uid)}`);
      link.textContent = uid;
      note.append(link);
    });
    note.append(document.createTextNode(
      entering.length === 1 ? " enters the path" : " enter the path"));
    row.append(note);
  }
  return row;
}
