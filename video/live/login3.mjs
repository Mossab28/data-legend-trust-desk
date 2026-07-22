import { chromium } from "playwright";
const PROFILE = new URL("./profile", import.meta.url).pathname;
const ctx = await chromium.launchPersistentContext(PROFILE, {
  headless: false,
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  viewport: { width: 1500, height: 950 },
  args: ["--window-size=1520,1010", "--hide-crash-restore-bubble"],
});
const p = ctx.pages()[0] ?? await ctx.newPage();
await p.goto("https://facility-trust-desk-7474647859757540.aws.databricksapps.com");
console.log(">> Utilise 'Continue with email' + le code reçu par mail (PAS le bouton Google).");
console.log(">> Quand l'app Facility Trust Desk est affichée, ferme simplement la fenêtre.");
await p.waitForEvent("close", { timeout: 0 }).catch(() => {});
// dump session aussi en state.json pour compat
try { await ctx.storageState({ path: "state.json" }); } catch {}
await ctx.close();
console.log("PROFILE_SAVED");
