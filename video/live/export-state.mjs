import { chromium } from "playwright";
const PROFILE = new URL("./profile", import.meta.url).pathname;
const ctx = await chromium.launchPersistentContext(PROFILE, {
  headless: true,
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
await ctx.storageState({ path: "state.json" });
await ctx.close();
console.log("state.json exporté");
