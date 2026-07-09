const fs = require("fs");
const vm = require("vm");
const path = require("path");
const katexPath = path.join(__dirname, "katex.min.js");
const code = fs.readFileSync(katexPath, "utf8");
const sandbox = { module: { exports: {} }, exports: {}, console };
sandbox.window = sandbox;
sandbox.self = sandbox;
sandbox.global = sandbox;
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const katex = sandbox.katex || sandbox.module.exports || sandbox.exports;
if (!katex || !katex.renderToString) {
  console.error("katex not loaded");
  process.exit(2);
}
const input = fs.readFileSync(0, "utf8");
let jobs;
try { jobs = JSON.parse(input); } catch (e) {
  console.error("bad json", e);
  process.exit(1);
}
const out = [];
for (const job of jobs) {
  try {
    const html = katex.renderToString(job.tex || "", {
      displayMode: !!job.display,
      throwOnError: false,
      strict: "ignore",
      output: "html"
    });
    out.push({ ok: true, html: html });
  } catch (e) {
    out.push({ ok: false, error: String(e && e.message ? e.message : e) });
  }
}
process.stdout.write(JSON.stringify(out));
