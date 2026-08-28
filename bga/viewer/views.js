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

// UX-316: the size scale, and the two exhibit affordances, from the one
// module that owns them. `drawings.js` imports nothing, so this is not a
// cycle - and the alternative was a second copy of the scale, which is
// the defect §2a exists to end (`viewBox: "0 0 100 20"` was written out
// by hand in this file).
import {
  SCALE, GRADE_ANNOTATION, GRADE_EXHIBIT, exhibitAxis, exhibitTwin,
} from "./drawings.js";
// UX-334: `name`/`id` on every control, and a `<label>` that points at
// one. `controls.js` imports nothing, which is why this module may use
// it where it may not use `app.js` - see the note below.
import { identify, labelFor } from "./controls.js";
// `UX-337`: the primitives the chapters share. Extracted because the
// chapters were *not* acyclic without them - see `primitives.js`.
import {
  SVG, svg, seconds, mib, bar, OVERVIEW_SHOWN, elementAnchor,
} from "./primitives.js";


// `UX-337`: this file was 2,531 lines. The element object moved to
// `element.js` and the decision panel to `decision.js`, along the
// chapter seams this file already carried - see those headers for the
// derivation that says the three are acyclic.
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

  // UX-316: exhibit grade, and the height is the scale's `figure` - a
  // composed drawing with lanes. The number is what it always was; what
  // changed is that it is now read from one place, so the grade walk can
  // hold it and a fourth drawing cannot invent a fifth height.
  const H = SCALE[GRADE_EXHIBIT].figure;
  const figure = svg("svg", {
    viewBox: `0 0 100 ${H}`, class: "band", preserveAspectRatio: "none",
    role: "img", "data-grade": GRADE_EXHIBIT, "data-where": geometry.where,
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
  // UX-316 (§2a): the band's twin. Every row is a published edge of
  // `compare/v1` - the geometry object holds the values beside the
  // positions, so the table and the drawing cannot disagree.
  wrapper.append(exhibitTwin(document, ["mark", "value"], [
    ["candidate", String(geometry.candidate.value)],
    ["band low", String(geometry.band.low)],
    ["band high", String(geometry.band.high)],
    ["observed low", String(geometry.observed.low)],
    ["observed high", String(geometry.observed.high)],
    ...geometry.runs.map((run, i) => [`baseline ${i + 1}`, String(run.value)]),
  ]));
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

export function renderTrend(store, schema = undefined,
                            aggregate = undefined) {
  // UX-335: a row that is not an object is not a snapshot. `store/v1`
  // says every entry is one, and a store written by a half-finished
  // prune or an interrupted snapshot can carry a `null` anyway - at
  // which point `r.total_duration_us` below threw and took the *page*
  // with it, not the trend. Dropped rather than drawn, and counted, so
  // the drawing can say it is speaking for fewer runs than the store
  // holds.
  const all = store?.snapshots ?? [];
  const rows = all.filter((row) => row && typeof row === "object");
  const unreadable = all.length - rows.length;
  if (rows.length < 2) return null;
  const markers = verdictMarkers(schema);

  // UX-316: the store diagram is exhibit grade - it is the section's
  // whole answer, and the field pass read it as "unreadable because
  // everything is very small". Its box comes from the scale's `spark`
  // (a line over an order is what this is), and the marks come from the
  // box: a dot written as `1.3` was a dot sized for a box of 40, and it
  // would have stayed that size while the box grew.
  const W = SCALE[GRADE_EXHIBIT].width, H = SCALE[GRADE_EXHIBIT].spark;
  const dot = H / 30;
  // UX-203: the axis is duration. It was `bytes`, so the trend
  // answered "is this project drifting" with disk usage.
  const sizes = rows.map((r) => r.total_duration_us ?? 0);
  const max = Math.max(...sizes, 1);
  const x = (i) => (rows.length === 1 ? W / 2 : (i / (rows.length - 1)) * W);
  const y = (v) => H - (v / max) * (H - dot * 4.5) - dot * 2.25;

  const figure = svg("svg", {
    viewBox: `0 0 ${W} ${H}`, class: "trend", preserveAspectRatio: "none",
    role: "img", "data-grade": GRADE_EXHIBIT, "data-points": rows.length,
  });
  // UX-234: the distribution the points come from, drawn behind them.
  // Every edge is a published figure of `store-aggregate/v1` - the page
  // picks no percentile and computes none - and nothing is drawn at all
  // when the store mixes host classes, because one band over two
  // machines is exactly the blend the aggregate refuses.
  const shape = trendDistribution(aggregate);
  if (shape) {
    figure.append(svg("rect", {
      x: 0, y: y(shape.p95), width: W,
      height: Math.max(0, y(shape.median) - y(shape.p95)),
      class: "trend-band", "data-band": "median-p95",
      "data-median": shape.median, "data-p95": shape.p95,
    }));
    figure.append(svg("line", {
      x1: 0, x2: W, y1: y(shape.median), y2: y(shape.median),
      class: "trend-median", "data-median": shape.median,
    }));
  }
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
          x: x(index) - dot, y: y(row.total_duration_us ?? 0) - dot,
          width: dot * 2, height: dot * 2,
          class: "trend-point incomplete", "data-marker": "square",
          "data-stamp": row.stamp, "data-incomplete": reason })
      : markerPoint(verdictMarker(verdict, markers), x(index),
                    y(row.total_duration_us ?? 0), dot, {
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
  // UX-335: and how many rows this drawing could not read at all. Said
  // rather than silently dropped - a trend over 3 of 4 snapshots that
  // presents itself as a trend over 4 is the kind of quiet wrong this
  // repository spends its rounds removing.
  if (unreadable) {
    caption.textContent += unreadable === 1
      ? ` \u00b7 1 row in this store could not be read and is not drawn`
      : ` \u00b7 ${unreadable} rows in this store could not be read and `
        + `are not drawn`;
    wrapper.setAttribute("data-unreadable-rows", String(unreadable));
  }
  wrapper.append(heading, figure);
  // UX-316 (§2a): an exhibit's ends are read, not hovered - and it is
  // paired with its table twin, so the drawing never hoards values a
  // reader wants as rows. Both are built from `rows`, which is what the
  // drawing itself was handed: no second reading of the store.
  wrapper.append(exhibitAxis(document, [
    { name: "first", at: 0, label: rows[0].stamp },
    { name: "peak", at: (sizes.indexOf(max) / Math.max(1, rows.length - 1)) * 100,
      label: seconds(max) },
    { name: "last", at: 100, label: rows[rows.length - 1].stamp },
  ]));
  wrapper.append(caption);
  wrapper.append(exhibitTwin(document, ["snapshot", "duration", "verdict"],
    rows.map((row) => [
      row.stamp,
      row.total_duration_us != null ? seconds(row.total_duration_us) : "—",
      row.incomplete_reason ? row.incomplete_reason
        : (row.verdict_kind ?? "—").replace(/_/g, " "),
    ])));
  // UX-234: what the band is, or why there is none. A refusal is data:
  // a chart that silently dropped its band would read as a store with
  // nothing to say about itself.
  const note = distributionNote(aggregate);
  if (note) {
    const line = document.createElement("p");
    line.className = "muted trend-distribution";
    line.setAttribute("data-distribution", shape ? "median-p95" : "refused");
    line.textContent = note;
    wrapper.append(line);
  }
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

/**
 * UX-234: the one distribution a trend may draw, or null.
 *
 * `blended` is published only when the store holds a single host class,
 * or when the caller passed `--blend` and took the mixed claim
 * themselves. The page never asks, so `mixes > 1` here means somebody
 * stated that claim on a command line, and a drawing is not the place
 * to inherit it.
 */
export function trendDistribution(aggregate) {
  const blended = aggregate?.blended;
  if (!blended || (blended.mixes ?? 1) !== 1) return null;
  const duration = blended.duration_us;
  if (!duration || duration.median == null || duration.p95 == null) return null;
  return duration;
}

/** The sentence under the trend: the distribution, or the refusal. */
export function distributionNote(aggregate) {
  if (!aggregate) return null;
  const shape = trendDistribution(aggregate);
  if (shape) {
    return `Median ${seconds(shape.median)} \u00b7 p95 ${seconds(shape.p95)}`
      + ` over ${shape.samples} finished run(s)`;
  }
  return aggregate.refusal?.sentence ?? null;
}

// ---------------------------------------------------------- blast box
//
// The search box is a *transport*: it hands the target to the server,
// which calls the same function `bga blast` calls. No resolution
// happens here, because a second resolver would be a second answer.

export function renderBlastSearch(onQuery) {
  const wrapper = document.createElement("section");
  wrapper.setAttribute("data-section", "blast");
  // `UX-348`: the rail names the capability. Both shapes of this
  // section carry the same label, because a reader looking for the
  // blast radius is looking for the same thing whether the page is
  // served or exported - what differs is how they get the answer, and
  // that difference is stated inside the section.
  wrapper.setAttribute("data-toc-label", "Blast radius");
  const heading = document.createElement("h2");
  heading.textContent = "What rebuilds if I touch this?";
  const form = document.createElement("form");
  form.setAttribute("data-role", "blast-form");
  const input = document.createElement("input");
  input.setAttribute("data-role", "blast-input");
  identify(input, "blast-query");
  input.setAttribute("aria-label", "What rebuilds if I touch this?");
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
 * `UX-348`: the same capability, in a document with no server behind it.
 *
 * What was here was a heading, one sentence of refusal and
 * `bga blast <target> <run>` - 103 px, a placeholder command with angle
 * brackets, in a chapter called "What if I change this?", under a rail
 * entry that read **"Blast offline"**. The navigation announced the
 * capability as unavailable, and the export could already spell the
 * command with this run's own path: two `next_steps` entries do, with a
 * Copy button.
 *
 * So this reads the published step rather than composing one. Direction
 * 7's boundary: the pipeline decides which element to ask about (the
 * longest thing on the chain, or the first thing to fix), and the page
 * prints what it decided. A run whose pipeline published no blast step
 * has no target to name, and the section says the interactive search
 * needs a server without inventing an element to pass it.
 */
export function renderBlastOffline(payload, copy, make) {
  const section = make("section", { "data-section": "blast",
                                    "data-toc-label": "Blast radius" });
  section.append(make("h2", {}, "Blast radius"));
  const step = (payload?.next_steps ?? []).find(
    (entry) => Array.isArray(entry?.argv) && entry.argv[1] === "blast");
  const argv = step ? step.argv.join(" ") : null;
  // `UX-282`'s rule: the difference between this page and a served one
  // is stated *inside* the section, not in its name.
  section.append(make("p", { class: "muted" },
    argv
      ? "The search box asks a server, and an exported report has none - "
        + "so here is the same answer as a command, for the element this "
        + "run ranks first:"
      : "The search box asks a server, and an exported report has none. "
        + "Run `bga blast` against this run with the element you are "
        + "about to change."));
  if (argv) {
    if (step.reason) {
      section.append(make("p", { class: "muted", "data-role": "blast-why" },
                          step.reason));
    }
    const command = make("code", { class: "next-command",
                                   "data-argv": argv }, argv);
    section.append(command);
    if (copy) {
      const button = make("button", { type: "button", class: "copy-step",
                                      "data-copies": "command",
                                      title: "Copy this command to the "
                                             + "clipboard, ready to run" },
                          "Copy command");
      button.addEventListener?.("click", () => {
        copy(argv);
        button.textContent = "\u2713 copied";
        setTimeout(() => { button.textContent = "Copy command"; }, 1200);
      });
      section.append(button);
    }
  }
  return section;
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
  const ranked = (payload?.elements?.top_blast_radius) || [];
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
      ? `${seconds(result.measured_us)} `
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
                host.memory_bytes
                  && `${Math.round(host.memory_bytes / 1024 ** 3)} GiB`]
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
  // `UX-320` (styleguide §3a.1): this folds **published values** and
  // said only "The numbers behind that" - a rabbit hole whose depth the
  // reader could not see. `UX-318` gave the rule to the value folds
  // `renderStructured` builds; the conformance pass found this one,
  // built by hand here, outside it. One level, `rows.length` rows.
  fold.setAttribute("data-levels", "1");
  fold.setAttribute("data-rows", String(rows.length));
  const summary = document.createElement("summary");
  summary.textContent =
    `The numbers behind that · 1 level, ${rows.length} `
    + `row${rows.length === 1 ? "" : "s"}`;
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


// `UX-319`: exported, because the chain has **two** surfaces - this
// drawing and the element listing `app.js` lifts into its own section -
// and one chain folded at two different places would be two chains.
export const PATH_HEAD = 6;
export const PATH_TAIL = 3;

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
  const detail = payload?.critical_path_detail;
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
  box.style.flexGrow =
    `${Math.max(0, Number(entry.share_of_path) || 0) * 1000}`;
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
    row.style.paddingLeft = `${depth * 1.4}rem`;
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
    if (typeof entry.measured_us === "number") {
      const cost = document.createElement("span");
      cost.className = "blast-cost num";
      cost.setAttribute("data-raw", String(entry.measured_us));
      cost.textContent = seconds(entry.measured_us);
      row.append(cost);
    }
    list.append(row);
  }
  section.append(list);
  return section;
}


