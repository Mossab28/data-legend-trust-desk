// record2.mjs — headless, clean-frame recording of the live app.
// Per handoff: viewport == recordVideo.size, no click markers, captions
// injected IN the page (local ffmpeg lacks libass), context closed before
// reading video.path(). Reuses the logged-in persistent profile.
//   node record2.mjs        → recordings/demo-raw.webm

import { chromium } from "playwright";
import fs from "fs";

const APP = "https://facility-trust-desk-7474647859757540.aws.databricksapps.com";
const PROFILE = new URL("./profile", import.meta.url).pathname;
const REC = new URL("./recordings", import.meta.url).pathname;
fs.mkdirSync(REC, { recursive: true });

const ctx = await chromium.launchPersistentContext(PROFILE, {
  headless: true,
  executablePath:
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  viewport: { width: 1920, height: 1080 },
  recordVideo: { dir: REC, size: { width: 1920, height: 1080 } },
});
const page = ctx.pages()[0] ?? (await ctx.newPage());
const wait = (ms) => page.waitForTimeout(ms);

async function idle(extra = 500) {
  try {
    await page.waitForSelector('[data-testid="stStatusWidget"]', {
      state: "detached", timeout: 60000 });
  } catch {}
  await wait(extra);
}

// DA-matched caption card, bottom center — baked into the recording.
const capLog = [];
let capT0 = 0;
const caption = (t) => {
  if (capT0) capLog.push({ t: +(((Date.now() - capT0) / 1000).toFixed(2)), text: t });
  // écran propre — sous-titres ajoutés en post via Remotion (timing maîtrisé)
};
const _setCaption = (t) => page.evaluate((t) => {
  let el = document.getElementById("__cap");
  if (!el) {
    el = document.createElement("div"); el.id = "__cap";
    document.body.appendChild(el);
    Object.assign(el.style, {
      position: "fixed", left: "50%", bottom: "44px",
      transform: "translateX(-50%)", maxWidth: "72%",
      background: "rgba(13,17,23,.92)", color: "#E6EDF3",
      border: "1px solid #262D37", padding: "16px 30px",
      borderRadius: "12px", textAlign: "center", zIndex: "2147483647",
      pointerEvents: "none",
      font: '600 27px/1.35 Inter,"Helvetica Neue",Arial,sans-serif',
      boxShadow: "0 8px 30px rgba(0,0,0,.45)",
    });
  }
  el.textContent = t;
}, t);

const yOf = (locator) => locator.evaluate(
  (el) => el.getBoundingClientRect().top + scrollY);

const smoothScroll = (y, d = 1400) =>
  page.evaluate(({ y, d }) => new Promise((r) => {
    const s = scrollY, dist = y - s, t0 = performance.now();
    const st = (n) => {
      const p = Math.min(1, (n - t0) / d);
      const e = p < 0.5 ? 2 * p * p : 1 - (-2 * p + 2) ** 2 / 2;
      scrollTo(0, s + dist * e);
      p < 1 ? requestAnimationFrame(st) : r();
    };
    requestAnimationFrame(st);
  }), { y, d });

// ------------------------------------------------------------------ take
await page.goto(APP, { waitUntil: "domcontentloaded" });
await idle(1200);
const main = page.locator('section[data-testid="stMain"], section.main').first();
capT0 = Date.now();

// ============ SECTION 1 · HOOK ============
await caption("In India, a hospital's ICU is often a claim — not a real capability.");
await wait(4200);

// ============ SECTION 2 · PICK A NEED ============
await caption("A planner picks a type of care and a region.");
const capability = main.getByTestId("stSelectbox").first();
await smoothScroll(Math.max(0, await yOf(capability) - 200), 900);
await wait(300);
await capability.click();
await page.keyboard.type("Surgery", { delay: 45 });
await wait(250);
await page.keyboard.press("Enter");
await idle();
const state = main.getByTestId("stSelectbox").nth(1);
await state.click();
await page.keyboard.type("Rajasthan", { delay: 45 });
await wait(250);
await page.keyboard.press("Enter");
await idle(600);
await caption("Every facility is ranked by the evidence behind its claims.");
const tiles = main.locator(".ftd-stats").first();
await smoothScroll(Math.max(0, await yOf(tiles).catch(() => 400) - 160), 1000);
await wait(2600);
await caption("Green: corroborated. Amber: only claimed. Gray: unknown.");
await wait(2800);

// ============ SECTION 3 · THE EVIDENCE ============
await caption("Open any facility to read the exact sentences behind its rating.");
const nameBox = page.getByPlaceholder("Find a facility by name…");
await smoothScroll(Math.max(0, await yOf(nameBox) - 220), 800);
await nameBox.click();
await nameBox.pressSequentially("Agarwal", { delay: 45 });
await nameBox.press("Enter");
await idle(700);
const expander = page.getByText("Evidence, gaps & review").first();
await smoothScroll(Math.max(0, await yOf(expander) - 260), 900);
await wait(400);
await expander.click();
await idle(600);
await smoothScroll(await page.evaluate(() => scrollY + 240), 900);
await wait(3000);

// ============ SECTION 4 · THE APP DOUBTS ITSELF ============
await caption("The app even audits itself — and overturns its own ratings.");
await wait(3600);
await caption("Here, our own validator disagrees with a corroborated score.");
await wait(3800);

// ============ SECTION 5 · HUMAN IN THE LOOP (temps fort) ============
await caption("So a human always has the final word.");
const note = page.getByPlaceholder(/I visited this facility/).first();
await smoothScroll(Math.max(0, await yOf(note) - 300), 900);
await wait(500);
await note.click();
await note.pressSequentially("Field check: surgery not confirmed on site.", { delay: 42 });
await wait(600);
await caption("The planner overrides the machine, in plain words.");
await wait(2400);
const saveBtn = page.getByRole("button", { name: "Save override" }).first();
await saveBtn.click();
await idle(1000);
// remonter en haut pour montrer le compteur d'humilité passer à 1
await smoothScroll(0, 1000);
await wait(900);
const counter = main.locator("text=/times a human corrected/").first();
await counter.scrollIntoViewIfNeeded().catch(() => {});
await wait(500);
await caption("Every correction is signed, kept for the team — and counted, out loud.");
await wait(4400);

// ============ SECTION 6 · DATA DESERT ≠ MEDICAL DESERT ============
await page.getByRole("tab", { name: "Medical deserts" }).click();
await idle(800);
await caption("Zoom out: 755 districts, joined with India's official health survey.");
await wait(1000);
const mapCanvas = page.locator("canvas").last();
await mapCanvas.evaluate((el) =>
  el.scrollIntoView({ behavior: "smooth", block: "center" })).catch(() => {});
await wait(2200);
await caption("Red is a real medical desert. Gray just means we don't know yet.");
await wait(4200);

// ============ SECTION 7 · THE DECISION + CLOSE ============
await page.getByRole("tab", { name: "Shortlist & decisions" }).click();
await idle(700);
await caption("One click exports a brief the team can actually defend.");
const dl = page.getByRole("button", { name: /Download decision brief/ }).first();
await smoothScroll(Math.max(0, await yOf(dl) - 320), 1100);
await wait(500);
await dl.click().catch(() => {});
await wait(2600);
await caption("Facility Trust Desk — live on Databricks Free Edition.");
await wait(3400);

capLog.push({ t: +(((Date.now() - capT0) / 1000).toFixed(2)), text: "(end)" });
fs.writeFileSync(`${REC}/captions.json`, JSON.stringify(capLog, null, 2));
const v = page.video();
await ctx.close(); // finalise la vidéo
fs.copyFileSync(await v.path(), `${REC}/demo-raw.webm`);
console.log("→ recordings/demo-raw.webm prêt");
