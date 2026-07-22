import { chromium } from "playwright";
const PROFILE = new URL("./profile", import.meta.url).pathname;
const ctx = await chromium.launchPersistentContext(PROFILE, {
  headless: true,
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  viewport: {width:1400,height:900},
});
const p = ctx.pages()[0] ?? await ctx.newPage();
await p.goto("https://facility-trust-desk-7474647859757540.aws.databricksapps.com", { waitUntil: "domcontentloaded" });
await p.waitForTimeout(7000);
console.log((await p.title()).includes("Login") ? "EXPIRÉE" : "SESSION OK");
await ctx.close();
