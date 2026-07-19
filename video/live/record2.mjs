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

const browser = await chromium.launch({
  executablePath:
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
});
const ctx = await browser.newContext({
  storageState: new URL("./state.json", import.meta.url).pathname,
  viewport: { width: 1920, height: 1080 },
  recordVideo: { dir: REC, size: { width: 1920, height: 1080 } },
});
const page = await ctx.newPage();
const wait = (ms) => page.waitForTimeout(ms);

async function idle(extra = 500) {
  try {
    await page.waitForSelector('[data-testid="stStatusWidget"]', {
      state: "detached", timeout: 60000 });
  } catch {}
  await wait(extra);
}

// DA-matched caption card, bottom center — baked into the recording.
const caption = (t) => page.evaluate((t) => {
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
await idle(1800);
const main = page.locator('section[data-testid="stMain"], section.main').first();

await caption("Facility Trust Desk — built for non-technical NGO planners, on Databricks Free Edition.");
await wait(3800);

// S1 · pick Surgery + Rajasthan
await caption("Every capability in this data is a claim, not a fact. The planner picks a care need and a region.");
const capability = main.getByTestId("stSelectbox").first();
await smoothScroll(Math.max(0, await yOf(capability) - 200), 1000);
await capability.click();
await page.keyboard.type("Surgery", { delay: 60 });
await wait(300);
await page.keyboard.press("Enter");
await idle();
const state = main.getByTestId("stSelectbox").nth(1);
await state.click();
await page.keyboard.type("Rajasthan", { delay: 60 });
await wait(300);
await page.keyboard.press("Enter");
await idle(600);
await caption("Ranked by evidence: corroborated, claimed only, or honestly unknown.");
const tiles = main.locator(".ftd-stats").first();
await smoothScroll(Math.max(0, await yOf(tiles).catch(() => 400) - 160), 1200);
await wait(2600);

// S2 · find the star facility
await caption("Search any facility by name.");
const nameBox = page.getByPlaceholder("Find a facility by name…");
await smoothScroll(Math.max(0, await yOf(nameBox) - 220), 900);
await nameBox.click();
await nameBox.pressSequentially("Agarwal", { delay: 65 });
await nameBox.press("Enter");
await idle(800);

// S3 · open evidence
await caption("Row-level citations: the exact sentences behind every rating.");
const expander = page.getByText("Evidence, gaps & review").first();
await smoothScroll(Math.max(0, await yOf(expander) - 260), 1100);
await wait(400);
await expander.click();
await idle(600);
await smoothScroll(await page.evaluate(() => scrollY + 240), 1100);
await wait(2200);
await caption("The app double-checks its own work — our validator overturned 378 of our own ratings.");
await wait(3000);

// S4 · signed override (tradeoff: no ground truth -> humans in charge)
await caption("No ground truth exists, so humans stay in charge: signed overrides, remembered for the team.");
const note = page.getByPlaceholder(/I visited this facility/).first();
await smoothScroll(Math.max(0, await yOf(note) - 340), 1000);
await note.click();
await note.pressSequentially("Field check: surgical capability not confirmed on site.", { delay: 30 });
const saveBtn = page.getByRole("button", { name: "Save override" }).first();
await saveBtn.click();
await idle(1400);

// S5 · medical deserts — scroll TO the map, header is not the point
await page.getByRole("tab", { name: "Medical deserts" }).click();
await idle(800);
await caption("755 districts, joined with the official NFHS-5 health survey.");
const mapCanvas = page.locator("canvas").last();
await smoothScroll(Math.max(0, await yOf(mapCanvas).catch(() => 600) - 130), 1500);
await wait(1400);
await caption("Solid red: proven unmet need. Hollow gray: unknown. A data desert is not a medical desert.");
await wait(3400);

// S6 · decision brief
await page.getByRole("tab", { name: "Shortlist & decisions" }).click();
await idle(700);
await caption("One click: an evidence-cited Decision Brief — a decision the team can defend.");
const dl = page.getByRole("button", { name: /Download decision brief/ }).first();
await smoothScroll(Math.max(0, await yOf(dl) - 320), 1300);
await wait(500);
await dl.click().catch(() => {});
await wait(2200);

await caption("Databricks Apps · serverless SQL · Genie · MLflow — live on Free Edition.");
await wait(3000);

const v = page.video();
await ctx.close(); // finalise la vidéo
fs.copyFileSync(await v.path(), `${REC}/demo-raw.webm`);
await browser.close();
console.log("→ recordings/demo-raw.webm prêt");
