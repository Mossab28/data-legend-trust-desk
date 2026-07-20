import React from "react";
import {
  AbsoluteFill,
  interpolate,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";

const FPS = 30;
const RAW_SECONDS = 75.8667; // trimmed screen.mp4 duration
const FINAL_SECONDS = 60;

// Caption schedule (start, end in FINAL seconds). Even, comfortable pacing —
// each line held long enough to read and to voice over.
const CAPTIONS: Array<[number, number, string]> = [
  [0.0, 3.32, "In India, an ICU is often a claim, not a capability."],
  [3.32, 9.05, "A planner picks a type of care and a region."],
  [9.05, 14.12, "Ranked by evidence — green proven, amber claimed, gray unknown."],
  [14.12, 20.97, "Open any facility to read the exact sentences behind its rating."],
  [20.97, 23.82, "The app audits — and overturns — its own ratings."],
  [23.82, 26.83, "Our validator disagrees with a corroborated score."],
  [26.83, 30.5, "So a human always has the final word."],
  [30.5, 35.5, "The planner overrides the machine, in plain words."],
  [35.5, 44.0, "Every correction is signed, kept — and counted, out loud."],
  [44.0, 48.0, "755 districts, joined with the NFHS-5 survey."],
  [48.0, 51.6, "Red is a real medical desert. Gray means we don't know yet."],
  [51.6, 55.2, "One click exports a brief the team can defend."],
  [55.2, 58.2, "Live on Databricks Free Edition."]
,
];

const Caption: React.FC<{ text: string; durationInFrames: number }> = ({
  text,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const inO = interpolate(frame, [0, 6], [0, 1], { extrapolateRight: "clamp" });
  const outO = interpolate(
    frame,
    [durationInFrames - 6, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 56,
      }}
    >
      <div
        style={{
          maxWidth: "74%",
          background: "rgba(13,17,23,0.92)",
          border: "1px solid #262D37",
          borderRadius: 14,
          padding: "20px 40px",
          textAlign: "center",
          color: "#E6EDF3",
          fontFamily: "Inter, 'Helvetica Neue', Arial, sans-serif",
          fontWeight: 600,
          fontSize: 34,
          lineHeight: 1.35,
          boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
          opacity: Math.min(inO, outO),
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

export const LiveDemo: React.FC = () => {
  // Play the raw screen recording back faster so it fits FINAL_SECONDS.
  const playbackRate = RAW_SECONDS / FINAL_SECONDS;
  const frame = useCurrentFrame();
  const total = FINAL_SECONDS * FPS;
  const fadeOut = interpolate(frame, [total - 18, total], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeIn = interpolate(frame, [0, 10], [0, 1], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ background: "#0D1117" }}>
      <AbsoluteFill style={{ opacity: Math.min(fadeIn, fadeOut) }}>
        <OffthreadVideo
          src={staticFile("screen.mp4")}
          playbackRate={playbackRate}
          muted
        />
      </AbsoluteFill>
      {CAPTIONS.map(([start, end, text], i) => (
        <Sequence
          key={i}
          from={Math.round(start * FPS)}
          durationInFrames={Math.round((end - start) * FPS)}
        >
          <Caption
            text={text}
            durationInFrames={Math.round((end - start) * FPS)}
          />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
