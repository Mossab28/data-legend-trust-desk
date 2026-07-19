import React from "react";
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { C, FONT, MONO_NUM } from "./theme";

// ---------------------------------------------------------------- helpers

export const useEnter = (delay = 0, damping = 200) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping } });
};

/** Scene shell: fades/slides in at start, fades out over the last 12 frames. */
export const SceneShell: React.FC<{
  children: React.ReactNode;
  durationInFrames: number;
}> = ({ children, durationInFrames }) => {
  const frame = useCurrentFrame();
  const inO = interpolate(frame, [0, 12], [0, 1], {
    extrapolateRight: "clamp",
  });
  const outO = interpolate(
    frame,
    [durationInFrames - 12, durationInFrames - 2],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: C.bg,
        fontFamily: FONT,
        color: C.text,
        opacity: Math.min(inO, outO),
        overflow: "hidden",
      }}
    >
      <Backdrop />
      <div style={{ position: "absolute", inset: 0, padding: "90px 120px" }}>
        {children}
      </div>
    </div>
  );
};

/** Subtle drifting grid + glow — the "living data" backdrop. */
const Backdrop: React.FC = () => {
  const frame = useCurrentFrame();
  const shift = (frame * 0.15) % 48;
  return (
    <>
      <div
        style={{
          position: "absolute",
          inset: -60,
          backgroundImage: `linear-gradient(${C.border}22 1px, transparent 1px),
             linear-gradient(90deg, ${C.border}22 1px, transparent 1px)`,
          backgroundSize: "48px 48px",
          backgroundPosition: `${shift}px ${shift * 0.6}px`,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 1100,
          height: 1100,
          left: "55%",
          top: "-30%",
          background: `radial-gradient(circle, ${C.accent}14 0%, transparent 60%)`,
        }}
      />
    </>
  );
};

export const Kicker: React.FC<{ children: React.ReactNode; delay?: number }> = ({
  children,
  delay = 0,
}) => {
  const s = useEnter(delay);
  return (
    <div
      style={{
        fontSize: 24,
        letterSpacing: "0.18em",
        textTransform: "uppercase",
        color: C.accent,
        fontWeight: 700,
        opacity: s,
        transform: `translateY(${(1 - s) * 14}px)`,
        marginBottom: 22,
      }}
    >
      {children}
    </div>
  );
};

export const Title: React.FC<{
  children: React.ReactNode;
  delay?: number;
  size?: number;
}> = ({ children, delay = 4, size = 84 }) => {
  const s = useEnter(delay);
  return (
    <div
      style={{
        fontSize: size,
        fontWeight: 800,
        letterSpacing: "-0.02em",
        lineHeight: 1.06,
        opacity: s,
        transform: `translateY(${(1 - s) * 26}px)`,
      }}
    >
      {children}
    </div>
  );
};

export const Sub: React.FC<{ children: React.ReactNode; delay?: number }> = ({
  children,
  delay = 10,
}) => {
  const s = useEnter(delay);
  return (
    <div
      style={{
        fontSize: 34,
        color: C.muted,
        marginTop: 28,
        maxWidth: 1250,
        lineHeight: 1.45,
        opacity: s,
        transform: `translateY(${(1 - s) * 18}px)`,
      }}
    >
      {children}
    </div>
  );
};

// ---------------------------------------------------------------- product atoms

export const Pill: React.FC<{
  color: string;
  label: string;
  delay?: number;
  size?: number;
}> = ({ color, label, delay = 0, size = 26 }) => {
  const s = useEnter(delay, 14);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 12,
        padding: `${size * 0.35}px ${size * 0.9}px`,
        borderRadius: 999,
        fontSize: size,
        fontWeight: 600,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        border: `2px solid ${color}55`,
        background: `${color}14`,
        color,
        transform: `scale(${s})`,
      }}
    >
      <span
        style={{
          width: size * 0.42,
          height: size * 0.42,
          borderRadius: "50%",
          background: color,
        }}
      />
      {label}
    </span>
  );
};

export const ScoreBar: React.FC<{
  score: number;
  color: string;
  low?: number;
  high?: number;
  delay?: number;
  width?: number;
}> = ({ score, color, low, high, delay = 0, width = 420 }) => {
  const s = useEnter(delay);
  return (
    <div
      style={{
        position: "relative",
        width,
        height: 10,
        borderRadius: 5,
        background: "#21262D",
      }}
    >
      {low !== undefined && high !== undefined && (
        <div
          style={{
            position: "absolute",
            left: `${low * 100}%`,
            width: `${(high - low) * 100 * s}%`,
            top: 0,
            height: "100%",
            background: `${color}30`,
            borderRadius: 5,
          }}
        />
      )}
      <div
        style={{
          position: "absolute",
          width: `${score * 100 * s}%`,
          height: "100%",
          background: color,
          borderRadius: 5,
        }}
      />
    </div>
  );
};

export const CountUp: React.FC<{
  to: number;
  delay?: number;
  duration?: number;
  size?: number;
  color?: string;
}> = ({ to, delay = 0, duration = 40, size = 110, color = C.text }) => {
  const frame = useCurrentFrame();
  const t = interpolate(frame, [delay, delay + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const eased = 1 - Math.pow(1 - t, 3);
  const val = Math.round(to * eased);
  return (
    <span
      style={{
        fontSize: size,
        fontWeight: 800,
        color,
        letterSpacing: "-0.02em",
        ...MONO_NUM,
      }}
    >
      {val.toLocaleString("en-US")}
    </span>
  );
};

export const Card: React.FC<{
  children: React.ReactNode;
  delay?: number;
  style?: React.CSSProperties;
}> = ({ children, delay = 0, style }) => {
  const s = useEnter(delay);
  return (
    <div
      style={{
        border: `1.5px solid ${C.border}`,
        borderRadius: 14,
        background: C.surface,
        padding: "30px 36px",
        opacity: s,
        transform: `translateY(${(1 - s) * 30}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

export const Quote: React.FC<{
  text: string;
  src: string;
  delay?: number;
}> = ({ text, src, delay = 0 }) => {
  const s = useEnter(delay);
  return (
    <div
      style={{
        borderLeft: `5px solid ${C.accent}`,
        background: C.surfaceAlt,
        borderRadius: "0 12px 12px 0",
        padding: "24px 32px",
        marginBottom: 22,
        opacity: s,
        transform: `translateX(${(1 - s) * -40}px)`,
      }}
    >
      <div style={{ fontSize: 32, color: C.textMid, lineHeight: 1.4 }}>
        “{text}”
      </div>
      <div
        style={{
          fontSize: 20,
          color: C.muted,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          marginTop: 10,
        }}
      >
        {src}
      </div>
    </div>
  );
};
