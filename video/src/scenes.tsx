import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { C, MONO_NUM } from "./theme";
import {
  Card,
  CountUp,
  Kicker,
  Pill,
  Quote,
  SceneShell,
  ScoreBar,
  Sub,
  Title,
  useEnter,
} from "./ui";

// ------------------------------------------------------------------ S1 · Hook
export const S1Hook: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const strike = interpolate(frame, [55, 75], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <SceneShell durationInFrames={durationInFrames}>
      <div style={{ marginTop: 150 }}>
        <Kicker>Databricks × Hack-Nation · Data Legend</Kicker>
        <Title size={110}>
          In India, an ICU is often{" "}
          <span style={{ position: "relative", whiteSpace: "nowrap" }}>
            <span style={{ color: C.amber }}>a claim</span>
            <span
              style={{
                position: "absolute",
                left: 0,
                top: "54%",
                height: 6,
                width: `${strike}%`,
                background: C.red,
              }}
            />
          </span>
          <br />— not a capability.
        </Title>
        <Sub delay={30}>
          Families drive six hours to a hospital that promised intensive care —
          and find a locked door.
        </Sub>
      </div>
    </SceneShell>
  );
};

// ------------------------------------------------------------- S2 · The data
export const S2Problem: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => (
  <SceneShell durationInFrames={durationInFrames}>
    <Kicker>The raw material</Kicker>
    <Title size={72}>Ten thousand messy records. Zero ground truth.</Title>
    <div style={{ display: "flex", gap: 40, marginTop: 70 }}>
      {[
        { n: 10088, l: "facilities across India", d: 8 },
        { n: 29047, l: "capability claims to verify", d: 18 },
        { n: 254, l: "spellings for 35 states", d: 28 },
      ].map((x, i) => (
        <Card key={i} delay={x.d} style={{ flex: 1, textAlign: "center" }}>
          <CountUp to={x.n} delay={x.d + 6} size={96} />
          <div style={{ fontSize: 28, color: C.muted, marginTop: 12 }}>
            {x.l}
          </div>
        </Card>
      ))}
    </div>
    <Sub delay={45}>
      Every field is self-reported. “Advanced surgery” might mean a da Vinci
      robot — or a locked room.
    </Sub>
  </SceneShell>
);

// ---------------------------------------------------------- S3 · The verdicts
export const S3Verdicts: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => (
  <SceneShell durationInFrames={durationInFrames}>
    <Kicker>Facility Trust Desk</Kicker>
    <Title size={72}>Every claim gets a verdict — with receipts.</Title>
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 30,
        marginTop: 66,
      }}
    >
      {[
        {
          color: C.green,
          label: "Corroborated",
          text: "2+ independent sources agree — equipment, procedures, narrative",
          score: 0.86,
          low: 0.72,
          high: 0.94,
          d: 10,
        },
        {
          color: C.amber,
          label: "Claimed only",
          text: "the facility says so — nothing independently confirms it",
          score: 0.42,
          low: 0.2,
          high: 0.68,
          d: 24,
        },
        {
          color: C.gray,
          label: "Unknown",
          text: "record too sparse to judge — honestly not a verdict",
          score: 0.15,
          low: 0.02,
          high: 0.55,
          d: 38,
        },
      ].map((v, i) => (
        <Card
          key={i}
          delay={v.d}
          style={{ display: "flex", alignItems: "center", gap: 44 }}
        >
          <div style={{ width: 330 }}>
            <Pill color={v.color} label={v.label} delay={v.d + 4} />
          </div>
          <ScoreBar
            score={v.score}
            low={v.low}
            high={v.high}
            color={v.color}
            delay={v.d + 8}
          />
          <div style={{ fontSize: 26, color: C.muted, flex: 1 }}>{v.text}</div>
        </Card>
      ))}
    </div>
    <Sub delay={58}>
      The shaded band is the uncertainty interval — what’s solid vs speculative,
      with no ground truth.
    </Sub>
  </SceneShell>
);

// ---------------------------------------------------------- S4 · The receipts
export const S4Receipts: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => (
  <SceneShell durationInFrames={durationInFrames}>
    <Kicker>No black box</Kicker>
    <Title size={72}>The exact sentences behind every verdict.</Title>
    <div style={{ marginTop: 60, maxWidth: 1450 }}>
      <Quote
        text="da Vinci Surgical System (Robotic Surgery) — 7 operating theatres"
        src="Equipment field"
        delay={12}
      />
      <Quote
        text="Performs endoscopic skull base and pituitary surgery"
        src="Procedure field"
        delay={26}
      />
      <Quote
        text="Plans to add five ICUs — excluded: future intent is not capability"
        src="Filtered out · aspirational claim"
        delay={40}
      />
    </div>
    <Sub delay={54}>
      “Proposed”, “under construction”, “not available” — detected, and never
      counted as evidence.
    </Sub>
  </SceneShell>
);

// --------------------------------------------------------- S5 · Self-audit
export const S5Validator: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const s = useEnter(34, 16);
  return (
    <SceneShell durationInFrames={durationInFrames}>
      <Kicker>Honesty as a feature</Kicker>
      <Title size={72}>The app audits itself — out loud.</Title>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 70,
          marginTop: 80,
        }}
      >
        <div>
          <CountUp to={378} delay={10} size={230} color={C.red} />
          <div style={{ fontSize: 32, color: C.muted, maxWidth: 460 }}>
            of our own “corroborated” ratings, overturned by our own validator
          </div>
        </div>
        <div
          style={{
            flex: 1,
            border: `2px solid ${C.red}66`,
            background: `${C.red}12`,
            borderRadius: 14,
            padding: "34px 40px",
            opacity: s,
            transform: `scale(${0.94 + s * 0.06})`,
          }}
        >
          <div style={{ fontSize: 30, fontWeight: 700, color: C.red }}>
            Our own validator disagrees with this rating.
          </div>
          <div style={{ fontSize: 27, color: C.textMid, marginTop: 14 }}>
            Scored CORROBORATED for surgery — yet no anesthesia or
            operating-theatre evidence anywhere in the record.
          </div>
        </div>
      </div>
      <Sub delay={50}>
        1,360 GPS positions contradict their PIN code. 170 “critical care”
        facilities show no digital sign of life. We flag our own data.
      </Sub>
    </SceneShell>
  );
};

// ------------------------------------------------------------ S6 · Deserts
// Stylized India silhouette (clockwise, 700×660 space).
const INDIA_PATH =
  "M258,18 L292,48 L330,66 L372,84 L402,80 L432,92 L475,108 L530,128 " +
  "L560,150 L538,168 L500,170 L472,192 L452,178 L432,196 L452,225 L438,258 " +
  "L415,300 L385,355 L352,415 L322,470 L300,520 L286,562 L272,600 L258,588 " +
  "L246,540 L236,488 L224,432 L212,372 L200,318 L186,262 L166,238 L128,232 " +
  "L96,214 L64,196 L84,164 L118,152 L158,150 L150,120 L172,92 L205,62 " +
  "L232,38 Z";

// Dots sit ON the landmass now (same 700×660 coordinate space).
const DOTS: Array<[number, number, string, boolean]> = [
  [240, 110, C.green, true], [300, 95, C.green, true], [360, 115, C.amber, true],
  [420, 130, C.green, true], [490, 140, C.amber, true], [520, 155, C.gray, false],
  [200, 175, C.amber, true], [260, 165, C.green, true], [330, 175, C.red, true],
  [395, 185, C.red, true], [150, 205, C.gray, false], [230, 235, C.amber, true],
  [300, 245, C.gray, false], [370, 260, C.red, true], [415, 290, C.gray, false],
  [250, 300, C.green, true], [320, 330, C.red, true], [380, 350, C.gray, false],
  [270, 380, C.amber, true], [330, 410, C.green, true], [300, 455, C.gray, false],
  [280, 500, C.red, true], [300, 540, C.green, true], [285, 575, C.amber, true],
];

const IndiaMap: React.FC = () => {
  const frame = useCurrentFrame();
  const draw = interpolate(frame, [0, 45], [2600, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fill = interpolate(frame, [30, 60], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <svg
      width={700}
      height={640}
      viewBox="0 0 700 660"
      style={{ position: "absolute", left: 0, top: 0 }}
    >
      <path
        d={INDIA_PATH}
        fill={C.surface}
        fillOpacity={fill * 0.9}
        stroke={C.accent}
        strokeOpacity={0.55}
        strokeWidth={3}
        strokeDasharray={2600}
        strokeDashoffset={draw}
        strokeLinejoin="round"
      />
    </svg>
  );
};

export const S6Deserts: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => (
  <SceneShell durationInFrames={durationInFrames}>
    <Kicker>755 districts · joined to the official NFHS-5 survey</Kicker>
    <Title size={68}>A data desert is not a medical desert.</Title>
    <div style={{ display: "flex", marginTop: 30, gap: 60 }}>
      <div style={{ position: "relative", width: 700, height: 620 }}>
        <IndiaMap />
        {DOTS.map(([x, y, color, solid], i) => {
          const d = 40 + i * 2;
          return (
            <Dot key={i} x={x} y={y} color={color} solid={solid} delay={d} />
          );
        })}
      </div>
      <div style={{ flex: 1, paddingTop: 60 }}>
        <Legend color={C.red} solid delay={20}
          text="Solid red — real unmet need, proven by external health indicators" />
        <Legend color={C.gray} solid={false} delay={34}
          text="Hollow gray — our records are empty here. An unknown, not a verdict" />
        <Legend color={C.green} solid delay={48}
          text="Green — covered, with reasonably rich records" />
        <div style={{ fontSize: 28, color: C.muted, marginTop: 44, lineHeight: 1.5 }}>
          Confusing the two sends help to the wrong place. This app never does.
        </div>
      </div>
    </div>
  </SceneShell>
);

const Dot: React.FC<{
  x: number; y: number; color: string; solid: boolean; delay: number;
}> = ({ x, y, color, solid, delay }) => {
  const s = useEnter(delay, 12);
  return (
    <div
      style={{
        position: "absolute",
        left: x, top: y,
        width: 34, height: 34,
        borderRadius: "50%",
        background: solid ? color : "transparent",
        border: `3.5px solid ${color}`,
        opacity: solid ? 0.92 : 0.75,
        transform: `scale(${s})`,
      }}
    />
  );
};

const Legend: React.FC<{
  color: string; solid: boolean; text: string; delay: number;
}> = ({ color, solid, text, delay }) => {
  const s = useEnter(delay);
  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 20, marginBottom: 26,
        opacity: s, transform: `translateX(${(1 - s) * 30}px)`,
      }}
    >
      <div
        style={{
          width: 30, height: 30, borderRadius: "50%",
          background: solid ? color : "transparent",
          border: `3px solid ${color}`, flexShrink: 0,
        }}
      />
      <div style={{ fontSize: 28, color: C.textMid }}>{text}</div>
    </div>
  );
};

// ------------------------------------------------------------ S7 · Override
export const S7Override: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const NOTE = "Field visit May 2026 — the ICU is real.";
  const chars = Math.floor(
    interpolate(frame, [22, 70], [0, NOTE.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );
  const saved = useEnter(84, 14);
  return (
    <SceneShell durationInFrames={durationInFrames}>
      <Kicker>Humans stay in charge</Kicker>
      <Title size={72}>Every correction is signed — and remembered.</Title>
      <Card delay={10} style={{ marginTop: 66, maxWidth: 1250 }}>
        <div style={{ fontSize: 26, color: C.muted }}>
          Override by <span style={{ color: C.textMid, fontWeight: 700 }}>
          a.sharma@ngo.org</span> · authenticated via Databricks SSO
        </div>
        <div
          style={{
            marginTop: 24, fontSize: 40, color: C.text,
            borderBottom: `2px solid ${C.border}`, paddingBottom: 16,
            minHeight: 64,
          }}
        >
          {NOTE.slice(0, chars)}
          <span style={{ color: C.accent }}>
            {chars < NOTE.length ? "▍" : ""}
          </span>
        </div>
        <div
          style={{
            display: "inline-block", marginTop: 28,
            background: `${C.green}18`, border: `2px solid ${C.green}66`,
            color: C.green, fontWeight: 700, fontSize: 26,
            padding: "12px 28px", borderRadius: 10,
            opacity: saved, transform: `scale(${0.9 + saved * 0.1})`,
          }}
        >
          Saved for the whole team
        </div>
      </Card>
      <Sub delay={95}>
        The header proudly counts every time a human corrected this app. We wear
        it as a badge.
      </Sub>
    </SceneShell>
  );
};

// --------------------------------------------------------------- S8 · Close
export const S8Close: React.FC<{ durationInFrames: number }> = ({
  durationInFrames,
}) => (
  <SceneShell durationInFrames={durationInFrames}>
    <div style={{ marginTop: 60 }}>
      <Kicker>Live on Databricks Free Edition</Kicker>
      <Title size={92}>
        Decisions a planner
        <br />
        can <span style={{ color: C.accent }}>defend</span>.
      </Title>
      <div
        style={{ display: "flex", gap: 18, marginTop: 56, flexWrap: "wrap" }}
      >
        {[
          "Databricks Apps", "Serverless SQL", "Delta Sharing",
          "AI embeddings", "Genie", "MLflow 3 Tracing", "Lakebase",
        ].map((t, i) => (
          <Chip key={t} text={t} delay={14 + i * 6} />
        ))}
      </div>
      <div style={{ marginTop: 70 }}>
        <Sub delay={60}>
          Facility Trust Desk — the trust layer for Indian healthcare.
        </Sub>
        <div
          style={{
            marginTop: 26, fontSize: 30, color: C.muted, ...MONO_NUM,
          }}
        >
          github.com/Mossab28/data-legend-trust-desk
        </div>
      </div>
    </div>
  </SceneShell>
);

const Chip: React.FC<{ text: string; delay: number }> = ({ text, delay }) => {
  const s = useEnter(delay, 15);
  return (
    <span
      style={{
        border: `2px solid ${C.border}`, background: C.surface,
        borderRadius: 999, padding: "14px 30px", fontSize: 28,
        color: C.textMid, fontWeight: 600,
        transform: `scale(${s})`,
      }}
    >
      {text}
    </span>
  );
};
