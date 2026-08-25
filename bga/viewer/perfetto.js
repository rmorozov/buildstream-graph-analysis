// UX-194: hand the timeline to ui.perfetto.dev, wholesale.
//
// Direction 7's timeline rule: none of our own, ever. Perfetto's
// renderer and its SQL engine are better than anything this project
// would write, and they are one `postMessage` away.
//
// **This is not an upload.** The bytes go tab-to-tab through
// `postMessage` and are processed in the browser; ui.perfetto.dev is a
// static site with no server side to send a trace to. It looks like an
// upload - a public URL opens and your build data appears in it - so
// the page says so out loud, and so do the docs.
//
// The protocol is Perfetto's documented deep-link handshake: open the
// UI, ping it until it answers PONG (it cannot receive a trace before
// its worker is up), then post the buffer once.

export const PERFETTO_ORIGIN = "https://ui.perfetto.dev";

// Perfetto's own example uses 50ms. The cap exists because a blocked
// pop-up never answers, and a page that pings forever looks like it is
// working.
const PING_INTERVAL_MS = 50;
const TIMEOUT_MS = 20000;

/**
 * Post `buffer` to a freshly opened Perfetto tab.
 *
 * `deps` is injectable so this can be driven by a scripted window
 * double in a test - the handshake is the part worth guarding, and it
 * is unobservable through a real browser in CI.
 *
 * Resolves when Perfetto has the bytes. Rejects if the tab never
 * answers (a blocked pop-up is the usual cause, and the message says
 * so, because "nothing happened" is the worst possible failure here).
 */
/**
 * The `?url=` deep link (`UX-198` item 2).
 *
 * A plain `<a href>`: no script, no pop-up policy, no activation. The
 * browser navigates, and Perfetto fetches the trace from this server
 * itself - which is why the server answers a CORS pre-flight from
 * Perfetto's origin and from nowhere else.
 *
 * Served mode only. An export has no server for Perfetto to fetch
 * from, so `postMessage` stays its only path and the link is not
 * rendered there.
 */
export function deepLink(traceUrl, origin = PERFETTO_ORIGIN) {
  return `${origin}/#!/?url=${encodeURIComponent(traceUrl)}`;
}

export function openTab(deps = {}) {
  const { open = (url) => window.open(url), origin = PERFETTO_ORIGIN } = deps;
  const tab = open(origin);
  if (!tab) {
    throw new Error(
      "The Perfetto tab did not open — your browser blocked the pop-up. " +
      "Use the direct link below, allow pop-ups for this page, or open " +
      "ui.perfetto.dev yourself and drag the trace file in.");
  }
  return tab;
}

/**
 * Post `buffer` into an already-open Perfetto tab.
 *
 * Split from the opening (`UX-198`) because *when* the tab is opened is
 * the whole bug: a browser grants a page transient activation on a
 * click and revokes it at the first `await`, so anything that opens a
 * window after fetching has already lost permission to.
 */
export function postTrace(tab, buffer, title, deps = {}) {
  const {
    addEventListener = (...a) => window.addEventListener(...a),
    removeEventListener = (...a) => window.removeEventListener(...a),
    setInterval: setEvery = setInterval,
    clearInterval: clearEvery = clearInterval,
    setTimeout: setLater = setTimeout,
    clearTimeout: clearLater = clearTimeout,
    origin = PERFETTO_ORIGIN,
  } = deps;

  return new Promise((resolve, reject) => {
    let pinger = null, timer = null;
    const done = (fn, value) => {
      clearEvery(pinger);
      clearLater(timer);
      removeEventListener("message", onMessage);
      fn(value);
    };

    function onMessage(event) {
      // Only Perfetto's own origin may answer. Not for confidentiality
      // - `postMessage` below names `origin` as the target, so the
      // bytes cannot reach anywhere else regardless. It is so a stray
      // PONG from some other frame cannot make us fire *early*, before
      // Perfetto's worker is up, which loses the trace into a silent
      // empty tab.
      if (event.origin !== origin) return;
      if (event.data !== "PONG") return;
      tab.postMessage({ perfetto: { buffer, title } }, origin);
      done(resolve, { title, bytes: buffer.byteLength ?? buffer.length ?? 0 });
    }

    addEventListener("message", onMessage);
    pinger = setEvery(() => tab.postMessage("PING", origin), PING_INTERVAL_MS);
    timer = setLater(() => done(reject, new Error(
      `ui.perfetto.dev did not answer within ${TIMEOUT_MS / 1000}s. The tab ` +
      `may have been blocked, or opened without network access.`)), TIMEOUT_MS);
  });
}

/** Bytes already in hand: open a tab and post into it.
 *
 * Returns a *rejected promise* rather than throwing when the pop-up is
 * blocked - `openTab` throws synchronously, and callers of this have
 * always been able to write `.catch(...)`. Changing that was not part
 * of `UX-198` and an existing guard caught it.
 */
export function openInPerfetto(buffer, title, deps = {}) {
  let tab;
  try {
    tab = openTab(deps);
  } catch (error) {
    return Promise.reject(error);
  }
  return postTrace(tab, buffer, title, deps);
}

/**
 * Fetch the served trace and hand it over.
 *
 * **The tab is opened before the first `await`, deliberately.**
 * `UX-198`: the field report was *"transition to perfetto works bad in
 * latest chrome, I was not able to open my traces in one click"*, and
 * the mechanism is transient activation. A click grants the page the
 * right to open a window; that right is gone by the time an `await`
 * resolves. The previous shape fetched the trace, awaited
 * `arrayBuffer()`, and only then opened - which survives a 25 KB local
 * file on a warm cache and is blocked for anything slower, which is
 * every real trace.
 *
 * So: open synchronously, fetch afterwards, post when both the PONG
 * and the bytes are in hand. If the fetch then fails, the tab is
 * closed rather than left showing an empty Perfetto.
 *
 * `handOff` is `async`, but everything before its first `await` runs
 * synchronously inside the caller's click handler - which is exactly
 * the window activation covers.
 */
/**
 * How big the served trace is, without reading a byte of it.
 *
 * `UX-299`. The transport has to be chosen by size, and the size is not
 * knowable at page load: finding it means rendering the trace, which
 * `UX-296` deliberately moved off the startup path. A `HEAD` asks the
 * server for the headers alone - the render happens once and is reused
 * by whichever transport wins - and `Content-Length` is the answer.
 *
 * `null` when the server does not say. An unknown size is treated as
 * small, because the alternative is refusing the transport that works
 * today for every capture that fits.
 */
export async function tracedSize(url, deps = {}) {
  const fetchIt = deps.fetch ?? ((u, init) => fetch(u, init));
  try {
    const response = await fetchIt(url, { method: "HEAD" });
    if (!response.ok) return null;
    const length = response.headers?.get?.("content-length");
    return length === null || length === undefined ? null : Number(length);
  } catch (error) {
    return null;
  }
}

export async function handOff(url = "timeline.json.gz", title = "bga timeline",
                              deps = {}) {
  const fetchIt = deps.fetch ?? ((u) => fetch(u));
  // `UX-299`: a caller that has already opened the tab passes it in.
  // The window may only be opened while the click's transient
  // activation holds - before the first `await` - so a caller that has
  // to measure the trace first opens once and hands the tab over,
  // rather than opening a second one after the size is known and
  // having the browser block it.
  const tab = deps.tab ?? openTab(deps);
  let response;
  try {
    response = await fetchIt(url);
  } catch (error) {
    tab.close?.();
    throw error;
  }
  if (!response.ok) {
    tab.close?.();
    throw new Error(
      `${url}: ${response.status}. This run has no timeline — it was ` +
      `captured with --no-keep-raw, or before UX-188.`);
  }
  // Perfetto sniffs gzip itself, so the compressed bytes go over as-is.
  // Measured on a real capture of examples/06: 272,964 B of merged
  // trace becomes 24,782 B, 9.1% - and that is what crosses the
  // postMessage boundary.
  let buffer;
  try {
    buffer = await response.arrayBuffer();
  } catch (error) {
    tab.close?.();
    throw error;
  }
  return postTrace(tab, buffer, title, deps);
}
