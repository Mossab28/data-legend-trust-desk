import { chromium } from "playwright";
const b = await chromium.launch({
  headless: false,
  executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  args: ["--window-size=1500,1000"],
});
const c = await b.newContext({ viewport: { width: 1500, height: 950 } });
const p = await c.newPage();
await p.goto("https://facility-trust-desk-7474647859757540.aws.databricksapps.com");
console.log("→ Connecte-toi (email + code, PAS le bouton Google). Quand l'app");
console.log("  Facility Trust Desk s'affiche, reviens ici — je sauvegarde tout seul.");
// attendre que l'app soit chargée (présence d'un selectbox) puis sauver
try {
  await p.waitForSelector('[data-testid="stSelectbox"]', { timeout: 0 });
  await p.waitForTimeout(1500);
  await c.storageState({ path: "state.json" });
  console.log("STATE_SAVED");
} catch (e) { console.log("ERR", e.message.split("\n")[0]); }
await b.close();
