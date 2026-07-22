import { chromium } from "playwright";
const PROFILE = new URL("./profile", import.meta.url).pathname;
const ctx = await chromium.launchPersistentContext(PROFILE, {
  headless: true, executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  viewport:{width:1600,height:1000} });
const p = ctx.pages()[0] ?? await ctx.newPage();
await p.goto("https://facility-trust-desk-7474647859757540.aws.databricksapps.com", { waitUntil: "domcontentloaded" });
await p.waitForTimeout(25000);
await p.screenshot({ path: "diag.png" });
const n = await p.locator('[data-testid="stSelectbox"]').count();
const running = await p.locator('[data-testid="stStatusWidget"]').count();
console.log("selectboxes:", n, "| statusWidget(running):", running);
console.log("err?", (await p.evaluate(()=>document.body.innerText)).match(/error|exception|traceback/i)?.[0] || "none");
await ctx.close();
