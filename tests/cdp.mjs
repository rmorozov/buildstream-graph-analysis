// UX-257: the whole CDP client. Node 22's built-in WebSocket and
// fetch, and nothing else - that is the argument for driving a browser
// directly rather than adding Playwright.
//
//   node cdp.mjs <port> <url> <width> <height> [--observe]  < expression
//
// Prints the JSON value the expression evaluated to. With `--observe`,
// prints `{value, console, csp, issues}` instead: everything the
// console was told, every security-policy violation the document
// reported, and every entry the Issues panel would show - all from
// this navigation onwards.
//
// `UX-334`: the console half exists because eleven CSP violations and
// four 404s per boot accumulated across ten rounds with nothing
// listening. `Runtime.consoleAPICalled` catches what the page says,
// `Runtime.exceptionThrown` what it throws, and `Log.entryAdded` what
// the *browser* says about the page - which is where a 404 on a
// subresource is reported, and nowhere else. The violation events are
// collected in-page instead: `securitypolicyviolation` fires on
// `document` with the directive on it, which is the name a reader
// needs, and `Log`'s rendering of the same event is a sentence.
const [, , port, url, width, height] = process.argv;
const observing = process.argv.includes("--observe");

let expression = "";
for await (const chunk of process.stdin) expression += chunk;

const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = targets.find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);

let id = 0;
const pending = new Map();
const send = (method, params = {}) => new Promise((resolve) => {
  const n = ++id;
  pending.set(n, resolve);
  ws.send(JSON.stringify({ id: n, method, params }));
});
const consoled = [];
const issues = [];
// Not until the navigation this run is about. `Log.enable` *replays*
// what the target has already logged and this browser is reused across
// loads, so without a gate the second page observed inherits the
// first's errors: measured, the served boot came back carrying three
// `file://` CORS errors from the exported boot before it, and
// `Log.clear` alone does not fix it - the replay is already in flight
// by the time the clear is acknowledged.
let recording = false;
ws.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    pending.get(message.id)(message.result);
    pending.delete(message.id);
    return;
  }
  if (!observing || !recording) return;
  const p = message.params ?? {};
  if (message.method === "Runtime.consoleAPICalled") {
    consoled.push({
      source: "console", level: p.type,
      text: (p.args ?? []).map(describe).join(" "),
      url: p.stackTrace?.callFrames?.[0]?.url ?? "",
    });
  } else if (message.method === "Runtime.exceptionThrown") {
    const d = p.exceptionDetails ?? {};
    consoled.push({
      source: "exception", level: "error",
      text: d.exception?.description ?? d.text ?? "",
      url: d.url ?? d.stackTrace?.callFrames?.[0]?.url ?? "",
    });
  } else if (message.method === "Audits.issueAdded") {
    // What the Issues panel shows. A different channel again: the
    // form-control complaints `UX-334` was filed over never reach the
    // console at all, so a guard that watched only `Log` would report
    // a clean page with two hundred issues in it.
    const detail = p.issue?.details ?? {};
    const [kind] = Object.keys(detail);
    const body = detail[kind] ?? {};
    issues.push({ code: p.issue?.code ?? "", kind: kind ?? "",
                  reason: body.errorType ?? body.reason ?? body.type ?? "" });
  } else if (message.method === "Log.entryAdded") {
    const e = p.entry ?? {};
    consoled.push({ source: e.source ?? "log", level: e.level,
                    text: e.text ?? "", url: e.url ?? "" });
  }
});

// A `RemoteObject` without `returnByValue`: the printable half, in the
// order Chrome itself would show it.
function describe(arg) {
  if (arg.type === "string") return arg.value;
  if ("value" in arg) return JSON.stringify(arg.value);
  return arg.description ?? arg.type;
}
await new Promise((resolve) => ws.addEventListener("open", resolve));

await send("Page.enable");
if (observing) {
  await send("Runtime.enable");
  await send("Log.enable");
  await send("Log.clear");
  await send("Audits.enable");
  // Before the document exists, so a violation from the first
  // stylesheet is caught. `Page.navigate` below is what runs it.
  await send("Page.addScriptToEvaluateOnNewDocument", {
    source: `window.__bgaCsp = [];
      document.addEventListener("securitypolicyviolation", (event) => {
        window.__bgaCsp.push({
          directive: event.effectiveDirective || event.violatedDirective,
          disposition: event.disposition,
          blocked: event.blockedURI,
          source: event.sourceFile || "",
          line: event.lineNumber || 0,
        });
      });`,
  });
}
await send("Emulation.setDeviceMetricsOverride", {
  width: Number(width), height: Number(height),
  deviceScaleFactor: 1, mobile: false,
});
// The replay drains here, discarded, and the gate opens on the
// navigation this run is about.
if (observing) await new Promise((resolve) => setTimeout(resolve, 300));
recording = true;
await send("Page.navigate", { url });
// The page is one file with inlined payloads and no network, so a fixed
// settle is enough and a load-event race is not worth the machinery.
await new Promise((resolve) => setTimeout(resolve, 1200));

const result = await send("Runtime.evaluate", {
  expression, returnByValue: true, awaitPromise: true,
});
if (result.exceptionDetails) {
  process.stderr.write(JSON.stringify(result.exceptionDetails, null, 1));
  process.exit(1);
}
const value = result.result.value ?? null;
let out = value;
if (observing) {
  const violations = await send("Runtime.evaluate", {
    expression: "window.__bgaCsp ?? []", returnByValue: true,
  });
  out = { value, console: consoled, csp: violations.result?.value ?? [],
          issues };
}
// `process.exit` is deliberately not called: stdout to a pipe is
// asynchronous, and exiting truncates a long report. Closing the
// socket is what lets the event loop drain and the process end.
process.stdout.write(JSON.stringify(out));
ws.close();
