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
const RAW_SECONDS = 72.4167; // re-recorded screen.mp4 duration (chrome-cropped)
const FINAL_SECONDS = 60;

// Caption schedule (start, end in FINAL seconds), re-timed to the new
// recording's actual on-screen moments (see video/public/screen.mp4).
const CAPTIONS: Array<[number, number, string]> = [
  [0.0, 6.5, "In India, an ICU is often a claim, not a capability."],
  [6.5, 12.0, "A planner picks a type of care and a region."],
  [12.0, 18.5, "Ranked by evidence — green proven, amber claimed, gray unknown."],
  [18.5, 22.0, "Open any facility to read the exact sentences behind its rating."],
  [22.0, 24.5, "The app audits — and overturns — its own ratings."],
  [24.5, 27.5, "Our validator disagrees with a corroborated score."],
  [27.5, 32.0, "So a human always has the final word."],
  [32.0, 37.0, "The planner overrides the machine, in plain words."],
  [37.0, 42.0, "Every correction is signed, kept — and counted, out loud."],
  [42.0, 46.0, "755 districts, joined with the NFHS-5 survey."],
  [46.0, 50.0, "Red is a real medical desert. Gray means we don't know yet."],
  [50.0, 55.0, "One click exports a brief the team can defend."],
  [55.0, 58.5, "Live on Databricks Free Edition."],
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
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
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
