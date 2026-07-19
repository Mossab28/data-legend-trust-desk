// record-demo.mjs — drives the LIVE Facility Trust Desk app and records it.
// Persistent profile keeps the Databricks login across runs.
//   1st run (login):  node record-demo.mjs --login     (headed; sign in once)
//   record a take:    node record-demo.mjs             (records ./out/*.webm + steps.json)
// Each step's timestamp is logged so subtitles can be burned in perfectly.

import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "fs";

const APP = "https://facility-trust-desk-7474647859757540.aws.databricksapps.com";
const PROFILE = new URL("./profile", import.meta.url).pathname;
const OUT = new URL("./out", import.meta.url).pathname;
const LOGIN_ONLY = process.argv.includes("--login");

const steps = [];
let t0 = 0;
const mark = (label) =>
  steps.push({ label, t: +((Date.now() - t0) / 1000).toFixed(2) });

// Fake visible cursor that glides to each click point.
const CURSOR_JS = `
  const c = document.createElement('div');
  c.id='__cur';
  c.style.cssText='position:fixed;z-index:999999;width:26px;height:26px;'+
    'border-radius:50%;background:rgba(47,129,247,.35);border:2.5px solid #2F81F7;'+
    'pointer-events:none;transition:left .45s cubic-bezier(.2,.7,.3,1),top .45s cubic-bezier(.2,.7,.3,1);'+
    'left:640px;top:400px;transform:translate(-50%,-50%)';
  document.body.appendChild(c);
  window.__moveCur=(x,y)=>{c.style.left=x+'px';c.style.top=y+'px';};
  window.__pulseCur=()=>{c.animate([{transform:'translate(-50%,-50%) scale(1)'},
    {transform:'translate(-50%,-50%) scale(1.6)'},{transform:'translate(-50%,-50%) scale(1)'}],
    {duration:320});};
`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function idle(page, extra = 600) {
  // Wait for Streamlit to stop running (status widget disappears).
  try {
    await page.waitForSelector('[data-testid="stStatusWidget"]', {
      state: "detached", timeout: 45000 });
  } catch {}
  await sleep(extra);
}

async function glideClick(page, locator) {
  const box = await locator.boundingBox();
  if (!box) throw new Error("no box");
  const x = box.x + box.width / 2, y = box.y + box.height / 2;
  await page.evaluate(([x, y]) => window.__moveCur(x, y), [x, y]);
  await sleep(650);
  await page.evaluate(() => window.__pulseCur());
  await sleep(150);
  await locator.click();
}

async function glideType(page, locator, text) {
  await glideClick(page, locator);
  await locator.pressSequentially(text, { delay: 55 });
}

const ctxOpts = {
  viewport: { width: 1920, height: 1080 },
  deviceScaleFactor: 1,
};
if (!LOGIN_ONLY) {
  mkdirSync(OUT, { recursive: true });
  ctxOpts.recordVideo = { dir: OUT, size: { width: 1920, height: 1080 } };
}

const ctx = await chromium.launchPersistentContext(PROFILE, {
  headless: false, ...ctxOpts,
  executablePath:
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  args: ["--window-size=1920,1120", "--hide-crash-restore-bubble"],
});
const page = ctx.pages()[0] ?? (await ctx.newPage());
await page.goto(APP, { waitUntil: "domcontentloaded" });

if (LOGIN_ONLY) {
  console.log("→ Connecte-toi à Databricks dans la fenêtre, jusqu'à voir");
  console.log("  l'app Facility Trust Desk. Puis FERME la fenêtre.");
  await page.waitForEvent("close", { timeout: 0 }).catch(() => {});
  await ctx.close();
  process.exit(0);
}

// ---------------------------------------------------------------- the take
await idle(page, 1500);
await page.addStyleTag({ content: "*{scroll-behavior:smooth}" });
await page.evaluate(CURSOR_JS);
t0 = Date.now();
mark("open");

// S1 · Surgery + Rajasthan (scope to the MAIN area — the sidebar also has selectboxes)
const main = page.locator('section[data-testid="stMain"], section.main').first();
const capability = main.getByTestId("stSelectbox").first();
await capability.scrollIntoViewIfNeeded();
await glideClick(page, capability);
await page.keyboard.type("Surgery", { delay: 70 });
await sleep(400);
await page.keyboard.press("Enter");
await idle(page); await page.evaluate(CURSOR_JS);
mark("capability_surgery");

const state = main.getByTestId("stSelectbox").nth(1);
await glideClick(page, state);
await page.keyboard.type("Rajasthan", { delay: 70 });
await sleep(400);
await page.keyboard.press("Enter");
await idle(page); await page.evaluate(CURSOR_JS);
mark("state_rajasthan");
await sleep(1800); // let the tiles + map breathe on camera

// S2 · find the star facility by name
const nameBox = page.getByPlaceholder("Find a facility by name…");
await glideType(page, nameBox, "Agarwal");
await nameBox.press("Enter");
await idle(page); await page.evaluate(CURSOR_JS);
mark("name_search");
await sleep(1200);

// S3 · open the evidence expander
const expander = page.getByText("Evidence, gaps & review").first();
await expander.scrollIntoViewIfNeeded();
await sleep(600);
await glideClick(page, expander);
await idle(page); await page.evaluate(CURSOR_JS);
mark("evidence_open");
await sleep(2600); // read the receipts + red banner

// S4 · override with a note
const note = page.getByPlaceholder(/I visited this facility/).first();
await note.scrollIntoViewIfNeeded();
await sleep(500);
await glideType(page, note, "Field visit — surgical capability NOT confirmed on site.");
mark("override_typed");
const saveBtn = page.getByRole("button", { name: "Save override" }).first();
await glideClick(page, saveBtn);
await idle(page, 1200); await page.evaluate(CURSOR_JS);
mark("override_saved");
await page.evaluate(() => window.scrollTo(0, 0));
await sleep(1600); // humility counter now shows 1

// S5 · Medical deserts tab
await glideClick(page, page.getByRole("tab", { name: "Medical deserts" }));
await idle(page); await page.evaluate(CURSOR_JS);
mark("deserts_tab");
await sleep(1200);
const map2 = page.locator("canvas").last();
await map2.scrollIntoViewIfNeeded().catch(() => {});
await sleep(2800); // admire the map

// S6 · Shortlist & decision brief
await glideClick(page, page.getByRole("tab", { name: "Shortlist & decisions" }));
await idle(page); await page.evaluate(CURSOR_JS);
mark("shortlist_tab");
await sleep(900);
const dl = page.getByRole("button", { name: /Download decision brief/ }).first();
await dl.scrollIntoViewIfNeeded();
await sleep(500);
await glideClick(page, dl);
mark("brief_downloaded");
await sleep(2200);

mark("end");
writeFileSync(`${OUT}/steps.json`, JSON.stringify(steps, null, 2));
console.log(JSON.stringify(steps, null, 2));
await ctx.close(); // flushes the video
console.log("→ vidéo .webm + steps.json dans video/live/out/");
