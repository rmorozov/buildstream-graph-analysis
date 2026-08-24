// UX-257: the whole CDP client. Node 22's built-in WebSocket and
// fetch, and nothing else - that is the argument for driving a browser
// directly rather than adding Playwright.
//
//   node cdp.mjs <port> <url> <width> <height>  < expression-on-stdin
//
// Prints the JSON value the expression evaluated to.
const [, , port, url, width, height] = process.argv;

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
ws.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    pending.get(message.id)(message.result);
    pending.delete(message.id);
  }
});
await new Promise((resolve) => ws.addEventListener("open", resolve));

await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", {
  width: Number(width), height: Number(height),
  deviceScaleFactor: 1, mobile: false,
});
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
process.stdout.write(JSON.stringify(result.result.value ?? null));
ws.close();
